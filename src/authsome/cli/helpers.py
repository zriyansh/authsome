"""CLI specific utilities for authsome."""

import functools
import ipaddress
import sys
import urllib.parse
from pathlib import Path
from typing import Any

from loguru import logger

from authsome.auth.models.provider import ProviderDefinition
from authsome.cli.context import ContextObj, common_options, pass_ctx
from authsome.utils import format_error_code


def handle_errors(func):
    """Catch exceptions and print cleanly or return machine JSON."""

    @functools.wraps(func)
    def wrapper(ctx_obj: ContextObj, *args, **kwargs):
        try:
            return func(ctx_obj, *args, **kwargs)
        except Exception as exc:
            if ctx_obj.json_output:
                ctx_obj.print_json({"error": exc.__class__.__name__, "message": str(exc)})
            else:
                ctx_obj.echo(f"Error: {exc}", err=True, color="red")
            sys.exit(format_error_code(exc))

    return wrapper


def auth_command(func):
    """Composite decorator combining common options, context injection, and error handling."""
    return common_options(pass_ctx(handle_errors(func)))


def setup_logging(verbose: bool, log_file: Path | None) -> None:
    """Enable authsome library logs and wire up sinks. CLI-only — never called from library code."""
    logger.remove()
    logger.enable("authsome")

    level = "DEBUG" if verbose else "WARNING"
    logger.add(sys.stderr, level=level, colorize=True, diagnose=False)
    if verbose:
        logger.debug("Verbose logging enabled.")

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            str(log_file),
            level="DEBUG",
            rotation="10 MB",
            retention=5,
            compression="zip",
            diagnose=False,
        )


def _validate_provider_endpoints(definition: Any, ctx_obj: ContextObj) -> list[tuple[str, str, bool]]:
    """Extract and validate provider endpoints for security."""
    endpoints_to_check: list[tuple[str, str, bool]] = []
    if definition.oauth:
        if definition.oauth.authorization_url:
            endpoints_to_check.append(("authorization_url", definition.oauth.authorization_url, False))
        if definition.oauth.token_url:
            endpoints_to_check.append(("token_url", definition.oauth.token_url, False))
        if definition.oauth.revocation_url:
            endpoints_to_check.append(("revocation_url", definition.oauth.revocation_url, False))
        if definition.oauth.device_authorization_url:
            endpoints_to_check.append(("device_authorization_url", definition.oauth.device_authorization_url, False))
        if definition.oauth.registration_endpoint:
            endpoints_to_check.append(("registration_endpoint", definition.oauth.registration_endpoint, False))
    if definition.host_url:
        endpoints_to_check.append(("host_url", definition.host_url, True))

    for name, val, is_host in endpoints_to_check:
        if "://" in val:
            parsed = urllib.parse.urlparse(val)
            if parsed.scheme != "https":
                ctx_obj.echo(f"Error: {name} must use HTTPS scheme ({val})", err=True, color="red")
                sys.exit(1)
            host = parsed.hostname
        else:
            host = val

        if host in ("localhost", "127.0.0.1", "::1"):
            ctx_obj.echo(f"Error: {name} cannot be localhost ({val})", err=True, color="red")
            sys.exit(1)

        if host:
            try:
                ipaddress.ip_address(host)
                ctx_obj.echo(f"Error: {name} cannot be a bare IP address ({val})", err=True, color="red")
                sys.exit(1)
            except ValueError:
                pass

    return endpoints_to_check


def _api_key_env_var(definition: ProviderDefinition) -> str | None:
    """Return the canonical API key environment variable for a provider."""
    if definition.api_key:
        env_var = getattr(definition.api_key, "env_var", None)
        if isinstance(env_var, str) and env_var.strip():
            return env_var.strip()

    if definition.export and definition.export.env:
        env_var = definition.export.env.get("api_key")
        if env_var and env_var.strip():
            return env_var.strip()

    return None
