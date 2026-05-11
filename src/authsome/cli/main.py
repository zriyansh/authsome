"""Command-line interface for authsome."""

import json as json_lib
import os
import pathlib
import sys
from pathlib import Path
from typing import Any

import click
import requests

from authsome import AuthenticationFailedError, FlowType, __version__, audit
from authsome.auth.models.enums import AuthType, ExportFormat
from authsome.auth.models.provider import ProviderDefinition
from authsome.cli.context import ContextObj, common_options, pass_ctx
from authsome.cli.daemon_control import (
    daemon_status,
    start_daemon,
    stop_daemon,
)
from authsome.cli.helpers import _api_key_env_var, _validate_provider_endpoints, handle_errors, setup_logging
from authsome.utils import connection_is_active, format_error_code, format_expires_at, redact


@click.group()
@click.version_option(__version__, "-v", "--version")
@click.option("--verbose", is_flag=True, default=False, help="Enable DEBUG logging to stderr.")
@click.option(
    "--log-file",
    "log_file",
    default=str(Path(os.environ.get("AUTHSOME_HOME", str(Path.home() / ".authsome"))) / "logs" / "authsome.log"),
    show_default=True,
    help="Path for the rotating log file. Pass empty string to disable.",
)
@common_options
@click.pass_context
def cli(ctx: click.Context, verbose: bool, log_file: str) -> None:
    """Authsome: Portable local authentication library for AI agents and tools."""
    resolved = Path(log_file) if log_file else None
    setup_logging(verbose=verbose, log_file=resolved)


@cli.command(name="list")
@common_options
@pass_ctx
@handle_errors
def list_cmd(ctx_obj: ContextObj) -> None:
    """List providers and connection states."""
    actx = ctx_obj.initialize()
    data = actx.runtime_client.list_connections()
    raw_list = data["connections"]
    by_source = data["by_source"]

    connected: dict[str, list[dict]] = {}
    for provider_group in raw_list:
        connected[provider_group["name"]] = provider_group["connections"]

    def build_provider_entry(provider_data, source: str) -> dict:
        provider = ProviderDefinition.model_validate(provider_data)
        conns = connected.get(provider.name, [])
        connections_out = []
        for conn in conns:
            c: dict = {
                "connection_name": conn["connection_name"],
                "is_default": conn.get("is_default", False),
                "auth_type": conn.get("auth_type"),
                "status": conn.get("status"),
            }
            if conn.get("scopes"):
                c["scopes"] = conn["scopes"]
            if conn.get("expires_at"):
                c["expires_at"] = conn["expires_at"]
            connections_out.append(c)
        return {
            "name": provider.name,
            "display_name": provider.display_name,
            "auth_type": provider.auth_type.value,
            "source": source,
            "connections": connections_out,
        }

    bundled_out = [build_provider_entry(p, "bundled") for p in by_source["bundled"]]
    custom_out = [build_provider_entry(p, "custom") for p in by_source["custom"]]

    if ctx_obj.json_output:
        ctx_obj.print_json({"bundled": bundled_out, "custom": custom_out})
        return

    rows: list[dict[str, Any]] = []
    for p in bundled_out + custom_out:
        provider_label = f"{p['display_name']} [{p['name']}]"
        if p["connections"]:
            for conn in p["connections"]:
                rows.append(
                    {
                        "provider_id": p["name"],
                        "provider": provider_label,
                        "source": p["source"],
                        "auth": p["auth_type"],
                        "connection": (
                            f"{conn['connection_name']} (default)"
                            if conn.get("is_default")
                            else conn["connection_name"]
                        ),
                        "status": conn["status"],
                        "expires_at": conn.get("expires_at"),
                        "expires": format_expires_at(conn.get("expires_at")) or "-",
                    }
                )
        else:
            rows.append(
                {
                    "provider_id": p["name"],
                    "provider": provider_label,
                    "source": p["source"],
                    "auth": p["auth_type"],
                    "connection": "-",
                    "status": "not_connected",
                    "expires_at": None,
                    "expires": "-",
                }
            )

    if not rows:
        ctx_obj.echo("No providers configured.")
        return

    connected_provider_ids = {row["provider_id"] for row in rows if connection_is_active(row)}
    connected_count = len(connected_provider_ids)
    ctx_obj.echo(f"Providers: {len(bundled_out) + len(custom_out)} total, {connected_count} connected")

    headers = {
        "provider": "Provider",
        "source": "Source",
        "auth": "Auth",
        "connection": "Connection",
        "status": "Status",
        "expires": "Expires",
    }
    widths = {
        key: max(len(headers[key]), *(len(row[key]) for row in rows))
        for key in ("provider", "source", "auth", "connection", "status", "expires")
    }

    def pad_field(text: str, key: str, color: str | None = None, bold: bool = False, dim: bool = False) -> str:
        if ctx_obj.no_color or (not color and not dim):
            return f"{text:<{widths[key]}}"
        styled = click.style(text, fg=color, bold=bold, dim=dim)
        padding = " " * (widths[key] - len(text))
        return f"{styled}{padding}"

    def render_row(row: dict[str, Any], is_header: bool = False, is_divider: bool = False) -> str:
        if is_header or is_divider:
            return (
                f"{row['provider']:<{widths['provider']}}  "
                f"{row['source']:<{widths['source']}}  "
                f"{row['auth']:<{widths['auth']}}  "
                f"{row['connection']:<{widths['connection']}}  "
                f"{row['status']:<{widths['status']}}  "
                f"{row['expires']:<{widths['expires']}}"
            ).rstrip()

        is_active = connection_is_active(row)

        if is_active:
            prov_color = "green"
            prov_bold = True
            conn_color = "cyan"
            status_color = "green"
            status_dim = False
            expires_color = "yellow"
        else:
            prov_color = None
            prov_bold = False
            conn_color = None
            expires_color = None
            if row["status"] == "not_connected":
                status_color = None
                status_dim = True
            else:
                status_color = "red"
                status_dim = False

        provider_str = pad_field(row["provider"], "provider", color=prov_color, bold=prov_bold)
        source_str = pad_field(row["source"], "source")
        auth_str = pad_field(row["auth"], "auth")
        connection_str = pad_field(row["connection"], "connection", color=conn_color)
        status_str = pad_field(row["status"], "status", color=status_color, bold=is_active, dim=status_dim)
        expires_str = pad_field(row["expires"], "expires", color=expires_color)

        return f"{provider_str}  {source_str}  {auth_str}  {connection_str}  {status_str}  {expires_str}".rstrip()

    ctx_obj.echo(render_row(headers, is_header=True))
    ctx_obj.echo(
        render_row(
            {key: "-" * widths[key] for key in ("provider", "source", "auth", "connection", "status", "expires")},
            is_divider=True,
        )
    )
    for row in rows:
        ctx_obj.echo(render_row(row))


@cli.command(name="log")
@click.option("-n", "--lines", default=50, help="Number of lines to show.")
@common_options
@pass_ctx
@handle_errors
def log_cmd(ctx_obj: ContextObj, lines: int) -> None:
    """View the authsome audit log."""
    actx = ctx_obj.initialize()
    audit_file = actx.home / "audit.log"
    if not audit_file.exists():
        if ctx_obj.json_output:
            ctx_obj.print_json([])
        else:
            ctx_obj.echo("No audit log found.", err=True, color="yellow")
        sys.exit(0)

    try:
        with open(audit_file, encoding="utf-8") as f:
            log_lines = f.readlines()

        target_lines = [line.strip() for line in log_lines[-lines:] if line.strip()]

        if ctx_obj.json_output:
            parsed_lines = [json_lib.loads(line) for line in target_lines]
            ctx_obj.print_json({"lines": parsed_lines})
        else:
            for line in target_lines:
                ctx_obj.echo(line)
    except Exception as e:
        if ctx_obj.json_output:
            ctx_obj.print_json({"error": str(e)})
        else:
            ctx_obj.echo(f"Error reading audit log: {e}", err=True, color="red")
        sys.exit(1)


@cli.command()
@click.argument("provider")
@click.option("--connection", default="default", help="Connection name.")
@click.option("--flow", help="Authentication flow override.")
@click.option("--scopes", help="Comma-separated scopes to request.")
@click.option("--base-url", help="Base URL for the provider (e.g. for GitHub Enterprise).")
@click.option("--force", is_flag=True, help="Overwrite an existing connection if it already exists.")
@common_options
@pass_ctx
@handle_errors
def login(
    ctx_obj: ContextObj,
    provider: str,
    connection: str,
    flow: str | None,
    scopes: str | None,
    base_url: str | None,
    force: bool,
) -> None:
    """Authenticate with a provider using its configured flow."""
    actx = ctx_obj.initialize()
    flow_value = FlowType(flow).value if flow else None
    scope_list = [s.strip() for s in scopes.split(",")] if scopes else None

    if force and not ctx_obj.quiet:
        ctx_obj.echo("Warning: Forcing login will overwrite any existing connection.", color="yellow")
    if not ctx_obj.json_output:
        ctx_obj.echo(f"Starting login for {provider}...", color="cyan")

    try:
        session_info = actx.runtime_client.start_login(
            provider=provider,
            connection=connection,
            flow=flow_value,
            scopes=scope_list,
            base_url=base_url,
            force=force,
        )
        session_id = session_info["id"]
        status = session_info.get("status")
        login_result = {"status": "started", "record_status": status}

        if status == "completed":
            login_result["status"] = "success"
        else:
            next_action = session_info.get("next_action", {"type": "none"})
            action_type = next_action.get("type")

            if action_type == "open_url":
                auth_url = next_action["url"]
                if not ctx_obj.json_output and not ctx_obj.quiet:
                    ctx_obj.echo("Opening browser to continue login...", color="cyan")
                    ctx_obj.echo(f"Visit: {auth_url}", color="cyan")
                import webbrowser

                try:
                    webbrowser.open(auth_url)
                except Exception:
                    pass

            if not ctx_obj.json_output and not ctx_obj.quiet:
                ctx_obj.echo(
                    "\nLogin process started. The connection will be updated automatically once complete.",
                    color="yellow",
                )
                ctx_obj.echo(f"Session ID: {session_id}")

        audit.log(
            "login", provider=provider, connection=connection, flow=flow or "unknown", status=login_result["status"]
        )
    except Exception:
        audit.log("login", provider=provider, connection=connection, status="failure")
        raise

    if ctx_obj.json_output:
        ctx_obj.print_json(
            {
                "status": login_result.get("status", "success"),
                "provider": provider,
                "connection": connection,
                "record_status": login_result.get("record_status"),
            }
        )
    elif login_result.get("status") == "success":
        ctx_obj.echo(
            f"Already logged in to {provider} ({connection}). Use the --force flag to overwrite and open the browser.",
            color="green",
        )
    elif login_result.get("status") == "started":
        ctx_obj.echo(
            f"Login started for {provider} ({connection}). Run 'authsome list' to verify completion.",
            color="green",
        )
    else:
        ctx_obj.echo(f"Successfully logged in to {provider} ({connection}).", color="green")


@cli.command(name="import-env")
@click.argument("provider", required=False)
@click.option("--connection", default="default", help="Connection name.")
@click.option("--dry-run", is_flag=True, help="Show what would be imported without writing credentials.")
@click.option("--force", is_flag=True, help="Re-import even when the stored key already matches.")
@common_options
@pass_ctx
@handle_errors
def import_env(ctx_obj: ContextObj, provider: str | None, connection: str, dry_run: bool, force: bool) -> None:
    """Import API keys from environment variables into authsome."""
    actx = ctx_obj.initialize()

    provider_defs: list[ProviderDefinition] = []
    if provider:
        provider_defs = [ProviderDefinition.model_validate(actx.runtime_client.get_provider(provider))]
    else:
        connections = actx.runtime_client.list_connections()
        by_source = connections.get("by_source", {})
        for source in ("bundled", "custom"):
            for provider_data in by_source.get(source, []):
                provider_defs.append(ProviderDefinition.model_validate(provider_data))

    results: list[dict[str, str]] = []
    imported = 0
    for definition in provider_defs:
        if definition.auth_type != AuthType.API_KEY:
            continue

        env_var = _api_key_env_var(definition)
        if not env_var:
            results.append({"provider": definition.name, "status": "skipped_no_env_mapping"})
            continue

        env_value = os.environ.get(env_var)
        if not env_value or not env_value.strip():
            results.append({"provider": definition.name, "status": "skipped_env_not_set", "env_var": env_var})
            continue
        api_key_value = env_value.strip()

        existing_record: dict[str, Any] | None = None
        try:
            existing_record = actx.runtime_client.get_connection(definition.name, connection)
        except Exception:
            existing_record = None

        if (
            not force
            and existing_record is not None
            and existing_record.get("status") == "connected"
            and existing_record.get("api_key") == api_key_value
        ):
            results.append({"provider": definition.name, "status": "skipped_unchanged", "env_var": env_var})
            continue

        if dry_run:
            results.append({"provider": definition.name, "status": "would_import", "env_var": env_var})
            continue

        session_info = actx.runtime_client.start_login(
            provider=definition.name,
            connection=connection,
            flow=FlowType.API_KEY.value,
            force=True,
        )
        session_id = session_info["id"]
        resume_info = actx.runtime_client.resume_login_session(session_id, api_key=api_key_value)
        if resume_info.get("status") != "completed":
            session_status = resume_info.get("status")
            raise RuntimeError(
                f"Import did not complete for provider '{definition.name}' (session status: {session_status})."
            )

        imported += 1
        results.append({"provider": definition.name, "status": "imported", "env_var": env_var})
        audit.log("import_env", provider=definition.name, connection=connection, source_env=env_var, status="success")

    if ctx_obj.json_output:
        ctx_obj.print_json({"provider": provider, "connection": connection, "dry_run": dry_run, "results": results})
    else:
        if not results:
            ctx_obj.echo("No API key providers found to process.", color="yellow")
        else:
            for item in results:
                env_hint = f" ({item['env_var']})" if item.get("env_var") else ""
                ctx_obj.echo(f"{item['provider']}: {item['status']}{env_hint}")
            if dry_run:
                ctx_obj.echo("Dry run only. No credentials were imported.", color="yellow")
            else:
                ctx_obj.echo(f"Imported {imported} provider(s).", color="green")


@cli.command()
@click.argument("provider")
@click.option("--connection", default="default", help="Connection name.")
@common_options
@pass_ctx
@handle_errors
def logout(ctx_obj: ContextObj, provider: str, connection: str) -> None:
    """Log out of a connection and remove local state."""
    actx = ctx_obj.initialize()
    actx.runtime_client.logout(provider, connection)
    audit.log("logout", provider=provider, connection=connection)

    if ctx_obj.json_output:
        ctx_obj.print_json({"status": "logged_out", "provider": provider, "connection": connection})
    else:
        ctx_obj.echo(f"Logged out of {provider} ({connection}).", color="green")


@cli.group(name="connection")
def connection_group() -> None:
    """Manage provider connections."""


@connection_group.command(name="set-default")
@click.argument("provider")
@click.argument("connection")
@common_options
@pass_ctx
@handle_errors
def set_default_connection(ctx_obj: ContextObj, provider: str, connection: str) -> None:
    """Set the default connection for a provider."""
    actx = ctx_obj.initialize()
    actx.runtime_client.set_default_connection(provider, connection)
    if ctx_obj.json_output:
        ctx_obj.print_json({"status": "ok", "provider": provider, "default_connection": connection})
    else:
        ctx_obj.echo(f"Default connection for {provider} set to {connection}.", color="green")


@cli.command()
@click.argument("provider")
@common_options
@pass_ctx
@handle_errors
def revoke(ctx_obj: ContextObj, provider: str) -> None:
    """Complete reset of the provider, removing all connections and client secrets."""
    actx = ctx_obj.initialize()
    actx.runtime_client.revoke(provider)
    audit.log("revoke", provider=provider, connection="all")

    if ctx_obj.json_output:
        ctx_obj.print_json({"status": "revoked", "provider": provider})
    else:
        ctx_obj.echo(f"Revoked all credentials for {provider}.", color="green")


@cli.command()
@click.argument("provider")
@common_options
@pass_ctx
@handle_errors
def remove(ctx_obj: ContextObj, provider: str) -> None:
    """Delete a custom provider definition."""
    actx = ctx_obj.initialize()
    actx.runtime_client.remove(provider)
    audit.log("remove", provider=provider, connection="all")

    if ctx_obj.json_output:
        ctx_obj.print_json({"status": "removed", "provider": provider})
    else:
        ctx_obj.echo(f"Removed provider {provider}.", color="green")


@cli.command()
@click.argument("provider")
@click.option("--connection", default="default", help="Connection name.")
@click.option("--field", help="Return only a specific field.")
@click.option("--show-secret", is_flag=True, help="Reveal encrypted secrets.")
@common_options
@pass_ctx
@handle_errors
def get(ctx_obj: ContextObj, provider: str, connection: str, field: str | None, show_secret: bool) -> None:
    """Return provider connection metadata by default."""
    actx = ctx_obj.initialize()
    # Verify provider exists first to raise ProviderNotFoundError if unknown
    actx.runtime_client.get_provider(provider)
    record_dict = actx.runtime_client.get_connection(provider, connection)
    from authsome.auth.models.connection import ConnectionRecord

    record = ConnectionRecord.model_validate(record_dict)

    if show_secret:
        from authsome.utils import require_os_auth

        if not require_os_auth("reveal secrets"):
            raise AuthenticationFailedError("Authentication failed or cancelled.")
        audit.log("get", provider=provider, connection=connection, field=field or "all")

    data = redact(record) if not show_secret else record.model_dump(mode="json")
    # Decouple from internal schema fields
    data.pop("schema_version", None)

    if field:
        if field in data:
            if show_secret:
                ctx_obj.echo(
                    "WARNING: Secret printed to stdout. Run: history -d <n> to remove from shell history.",
                    err=True,
                    color="yellow",
                )
            if ctx_obj.json_output:
                ctx_obj.print_json({field: data[field]})
                sys.exit(0)
            else:
                ctx_obj.echo(str(data[field]))
        else:
            ctx_obj.echo(f"Field '{field}' not found.", err=True, color="red")
            sys.exit(1)
        return

    if show_secret:
        ctx_obj.echo(
            "WARNING: Secret printed to stdout. Run: history -d <n> to remove from shell history.",
            err=True,
            color="yellow",
        )

    if ctx_obj.json_output:
        ctx_obj.print_json(data)
        sys.exit(0)
    else:
        for k, v in data.items():
            ctx_obj.echo(f"{k}: {v}")


@cli.command()
@click.argument("provider")
@common_options
@pass_ctx
@handle_errors
def inspect(ctx_obj: ContextObj, provider: str) -> None:
    """Return provider definition and local connection summary."""
    actx = ctx_obj.initialize()
    definition_dict = actx.runtime_client.get_provider(provider)
    data = definition_dict
    data["connections"] = []
    connections_data = actx.runtime_client.list_connections()
    for provider_group in connections_data["connections"]:
        if provider_group["name"] == provider:
            data["connections"] = provider_group["connections"]
            break

    if ctx_obj.json_output:
        data.pop("schema_version", None)
        ctx_obj.print_json(data)
    else:
        ctx_obj.echo(json_lib.dumps(data, indent=2))


@cli.command()
@click.argument("provider", required=False)
@click.option("--connection", default="default", help="Connection name.")
@click.option("--format", "export_format", type=click.Choice(["env", "json", "shell"]), default="env")
@common_options
@pass_ctx
@handle_errors
def export(ctx_obj: ContextObj, provider: str | None, connection: str, export_format: str) -> None:
    """Export credential material in selected format."""
    actx = ctx_obj.initialize()
    fmt = ExportFormat(export_format)
    output = actx.runtime_client.export(provider, connection, format=fmt.value)
    audit.log("export", provider=provider, connection=connection, format=fmt.value)
    if ctx_obj.json_output:
        # Call with format=json and parse the result to properly wrap with version info
        output_str = actx.runtime_client.export(provider, connection, format="json")
        try:
            data = json_lib.loads(output_str)
        except Exception:
            data = {}
        ctx_obj.print_json({"credentials": data})
        return

    ctx_obj.echo(
        "Note: secrets are now in your shell environment for this session. Prefer 'authsome run' for scoped injection.",
        err=True,
        color="yellow",
    )

    if output:
        click.echo(output)


@cli.command(context_settings=dict(ignore_unknown_options=True))
@click.argument("command", nargs=-1, required=True)
@common_options
@pass_ctx
@handle_errors
def run(ctx_obj: ContextObj, command: tuple[str]) -> None:
    """Run a subprocess behind the local auth proxy."""
    actx = ctx_obj.initialize()
    result = actx.require_local_proxy().run(list(command))
    sys.exit(result.returncode)


@cli.command()
@click.argument("path")
@click.option("--force", is_flag=True, help="Force overwrite if provider exists.")
@click.option("--yes", is_flag=True, help="Skip the registration confirmation prompt.")
@common_options
@pass_ctx
@handle_errors
def register(ctx_obj: ContextObj, path: str, force: bool, yes: bool) -> None:
    """Register a provider definition from a local JSON file path."""

    actx = ctx_obj.initialize()
    filepath = pathlib.Path(path)
    if not filepath.exists():
        ctx_obj.echo(f"File not found: {path}", err=True, color="red")
        sys.exit(1)

    try:
        data = json_lib.loads(filepath.read_text(encoding="utf-8"))
        from authsome.auth.models.provider import ProviderDefinition

        definition = ProviderDefinition.model_validate(data)

        # 1. Extract and validate endpoints
        endpoints_to_check = _validate_provider_endpoints(definition, ctx_obj)

        # 3. Confirmation prompt
        if not ctx_obj.json_output and not ctx_obj.quiet and not yes:
            ctx_obj.echo(f"Registering '{definition.name}' provider:")
            for name, val, _ in endpoints_to_check:
                ctx_obj.echo(f"  - {name}: {val}")

            if definition.oauth and definition.oauth.token_url:
                prompt_msg = f"Register '{definition.name}' with token endpoint {definition.oauth.token_url}? [y/N]"
            elif definition.host_url:
                prompt_msg = f"Register '{definition.name}' with host {definition.host_url}? [y/N]"
            else:
                prompt_msg = f"Register '{definition.name}' provider? [y/N]"

            if not click.confirm(prompt_msg, default=False):
                ctx_obj.echo("Registration aborted.", color="yellow")
                sys.exit(0)

        actx.runtime_client.register_provider(definition.model_dump(mode="json"), force=force)

        endpoints = [ep for _, ep, _ in endpoints_to_check]
        audit.log("register", provider=definition.name, endpoints=endpoints)

        if ctx_obj.json_output:
            ctx_obj.print_json({"status": "registered", "provider": definition.name})
        else:
            ctx_obj.echo(f"Provider {definition.name} registered.", color="green")

        # 4. Post-registration connectivity check

        warnings = []
        for name, val, is_host in endpoints_to_check:
            if name not in ("host_url", "authorization_url"):
                continue

            target = val
            if is_host and "://" not in target:
                target = f"https://{target}"

            if not ctx_obj.quiet:
                ctx_obj.echo(f"Testing reachability for {name}...", color="cyan")
            try:
                requests.head(target, timeout=5, allow_redirects=True)
            except requests.RequestException as e:
                warnings.append(f"{name} ({val}) is unreachable: {e}")

        if warnings and not ctx_obj.quiet:
            for w in warnings:
                ctx_obj.echo(f"Warning: {w}", color="yellow")

    except Exception as exc:
        ctx_obj.echo(f"Failed to register provider: {exc}", err=True, color="red")
        sys.exit(format_error_code(exc))


@cli.command()
@common_options
@pass_ctx
@handle_errors
def whoami(ctx_obj: ContextObj) -> None:
    """Show basic local context."""
    actx = ctx_obj.initialize()

    # Get info from daemon
    whoami_data = actx.runtime_client.whoami()
    doctor_results = actx.doctor()

    vault_status = "OK" if doctor_results.get("checks", {}).get("vault") == "ok" else "ERROR"

    # Connected providers with counts
    connected_providers = []
    connections_data = actx.runtime_client.list_connections()
    for provider_group in connections_data["connections"]:
        active_conns = [c["connection_name"] for c in provider_group["connections"] if connection_is_active(c)]
        if active_conns:
            connected_providers.append(
                {
                    "name": provider_group["name"],
                    "count": len(active_conns),
                    "connections": active_conns,
                }
            )

    data = {
        "authsome_version": whoami_data["version"],
        "home_directory": whoami_data["home"],
        "active_identity": whoami_data["active_identity"],
        "encryption_backend": whoami_data["encryption_backend"],
        "vault_status": vault_status,
        "connected_providers_count": len(connected_providers),
        "connected_providers": connected_providers,
    }

    if ctx_obj.json_output:
        ctx_obj.print_json(data)
    else:
        ctx_obj.echo(f"Authsome Version:  {data['authsome_version']}")
        ctx_obj.echo(f"Home Directory:    {data['home_directory']}")
        ctx_obj.echo(f"Active Identity:   {data['active_identity']}")
        status_color = "green" if vault_status == "OK" else "red"
        ctx_obj.echo(f"Encryption:        {data['encryption_backend']} [", nl=False)
        ctx_obj.echo(vault_status, color=status_color, nl=False)
        ctx_obj.echo("]")

        ctx_obj.echo(f"\nConnected Providers: {data['connected_providers_count']}")
        if connected_providers:
            for p in sorted(connected_providers, key=lambda x: x["name"]):
                suffix = "connection" if p["count"] == 1 else "connections"
                ctx_obj.echo(f"  {p['name']} ({p['count']} {suffix})")


@cli.command()
@common_options
@pass_ctx
@handle_errors
def doctor(ctx_obj: ContextObj) -> None:
    """Run health checks on directory layout and encryption."""
    actx = ctx_obj.initialize()
    results = actx.doctor()

    if ctx_obj.json_output:
        ctx_obj.print_json(results)
    else:
        all_ok = results.get("status") == "ready"
        for key, val in results.get("checks", {}).items():
            ok = val == "ok"
            ctx_obj.echo(f"{key}: ", nl=False)
            ctx_obj.echo("OK" if ok else "FAIL", color="green" if ok else "red")
        issues = results.get("issues", [])
        if issues:
            ctx_obj.echo("\nIssues found:", color="red")
            for issue in issues:
                ctx_obj.echo(f" - {issue}", color="red")

        warnings = results.get("warnings", [])
        if warnings:
            ctx_obj.echo("\nWarnings:", color="yellow")
            for warning in warnings:
                ctx_obj.echo(f" - {warning}", color="yellow")

        if not all_ok:
            sys.exit(1)


@cli.command()
@click.option("--no-browser", is_flag=True, help="Print the URL instead of opening a browser.")
@common_options
@pass_ctx
@handle_errors
def ui(ctx_obj: ContextObj, no_browser: bool) -> None:
    """Open the daemon dashboard in the browser."""
    actx = ctx_obj.initialize()
    url = f"{actx.runtime_client.base_url}/ui/"
    if no_browser:
        ctx_obj.echo(url)
        return

    import webbrowser

    ctx_obj.echo(f"Opening Authsome UI at {url}")
    webbrowser.open(url)


@cli.group()
def daemon() -> None:
    """Manage the local Authsome daemon."""


@daemon.command(name="serve")
@click.option("--host", default="127.0.0.1", show_default=True, help="Host interface to bind.")
@click.option("--port", default=7998, type=int, show_default=True, help="TCP port to listen on.")
@click.option("--reload", is_flag=True, help="Enable auto-reload on code changes.")
def daemon_serve(host: str, port: int, reload: bool) -> None:
    """Run the daemon in the foreground."""
    from authsome.server.daemon import serve

    serve(host=host, port=port, reload=reload)


@daemon.command(name="start")
@common_options
@pass_ctx
@handle_errors
def daemon_start(ctx_obj: ContextObj) -> None:
    """Start the local daemon in the background."""
    start_daemon()
    ctx_obj.echo("Daemon start requested.", color="green")


@daemon.command(name="stop")
@common_options
@pass_ctx
@handle_errors
def daemon_stop(ctx_obj: ContextObj) -> None:
    """Stop the local daemon."""
    stop_daemon()
    ctx_obj.echo("Daemon stopped.", color="green")


@daemon.command(name="restart")
@common_options
@pass_ctx
@handle_errors
def daemon_restart(ctx_obj: ContextObj) -> None:
    """Restart the local daemon."""
    stop_daemon()
    start_daemon()
    ctx_obj.echo("Daemon restart requested.", color="green")


@daemon.command(name="status")
@common_options
@pass_ctx
@handle_errors
def daemon_status_cmd(ctx_obj: ContextObj) -> None:
    """Show daemon status."""
    status = daemon_status()
    if ctx_obj.json_output:
        ctx_obj.print_json(status)
    else:
        ctx_obj.echo(json_lib.dumps(status, indent=2))


@daemon.command(name="logs")
@click.option("-n", "--lines", default=80, help="Number of lines to show.")
@common_options
@pass_ctx
@handle_errors
def daemon_logs(ctx_obj: ContextObj, lines: int) -> None:
    """Show daemon log output."""
    from authsome.cli.daemon_control import LOG_FILE

    if not LOG_FILE.exists():
        ctx_obj.echo(f"No daemon log found at {LOG_FILE}", err=True, color="yellow")
        return
    for line in LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]:
        ctx_obj.echo(line)


if __name__ == "__main__":
    cli()
