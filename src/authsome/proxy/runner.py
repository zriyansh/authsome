"""Subprocess runner that launches commands behind the local auth proxy."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Protocol

from loguru import logger

from authsome.proxy.server import RunningProxy, start_proxy_server


class ProxyClient(Protocol):
    async def list_connections(self) -> Any: ...

    async def get_provider(self, provider: str) -> Any: ...

    async def resolve_credentials(self, **kwargs: Any) -> Any: ...

    async def proxy_routes(self) -> Any: ...

    async def list_providers_by_source(self) -> Any: ...


class ProxyRunner:
    """Launch a subprocess behind the Authsome local auth proxy."""

    def __init__(self, client: ProxyClient) -> None:
        self._client = client

    async def run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        """Run *command* behind the auth-injecting proxy."""
        proxy_url, server = self._start_proxy()
        env = os.environ.copy()
        env["HTTP_PROXY"] = proxy_url
        env["HTTPS_PROXY"] = proxy_url
        env["http_proxy"] = proxy_url
        env["https_proxy"] = proxy_url
        existing_no_proxy = ",".join(filter(None, [env.get("NO_PROXY", ""), env.get("no_proxy", "")]))
        no_proxy = self._merge_no_proxy(existing_no_proxy)
        env["NO_PROXY"] = no_proxy
        env["no_proxy"] = no_proxy
        env["AUTHSOME_PROXY_MODE"] = "true"

        # Set dummy env vars for connected providers so SDKs that require
        # e.g. OPENAI_API_KEY to be set will initialise and route through the proxy
        await self._inject_dummy_credentials(env)

        # Build a combined CA bundle so subprocesses trust the mitmproxy CA
        ca_bundle_path = self._build_ca_bundle(server)
        keychain_cert_added = False
        if ca_bundle_path:
            env["SSL_CERT_FILE"] = str(ca_bundle_path)
            env["REQUESTS_CA_BUNDLE"] = str(ca_bundle_path)
            env["CURL_CA_BUNDLE"] = str(ca_bundle_path)
            # NODE_EXTRA_CA_CERTS adds to (not replaces) Node's built-in CAs
            env["NODE_EXTRA_CA_CERTS"] = str(server.ca_cert_path)
            logger.debug("CA bundle injected: {}", ca_bundle_path)
            # On macOS, Go's crypto/x509 ignores SSL_CERT_FILE and delegates to
            # the native Security framework, so we must add the CA to the login
            # keychain for tools like gh, terraform, and kubectl to trust it.
            keychain_cert_added = self._add_ca_to_macos_keychain(server.ca_cert_path)

        try:
            return subprocess.run(command, env=env, capture_output=False, text=True, check=False)
        finally:
            server.shutdown()
            if keychain_cert_added:
                self._remove_ca_from_macos_keychain()
            # Clean up the temporary CA bundle
            if ca_bundle_path and ca_bundle_path.exists():
                try:
                    ca_bundle_path.unlink()
                except OSError:
                    pass

    def _start_proxy(self) -> tuple[str, RunningProxy]:
        server = start_proxy_server(self._client)
        return server.url, server

    async def _inject_dummy_credentials(self, env: dict[str, str]) -> None:
        connections_data = await self._client.list_connections()
        if isinstance(connections_data, list):
            by_source = await self._client.list_providers_by_source()
            connections_data = {
                "connections": connections_data,
                "by_source": {
                    source: [provider.model_dump(mode="json") for provider in providers]
                    for source, providers in by_source.items()
                },
            }
        connected_names = {entry["name"] for entry in connections_data["connections"]}
        from authsome.auth.models.provider import ProviderDefinition

        for source_providers in connections_data["by_source"].values():
            for provider_dict in source_providers:
                provider = ProviderDefinition.model_validate(provider_dict)
                if provider.name not in connected_names:
                    continue
                if not provider.export or not provider.export.env:
                    continue
                for env_var in provider.export.env.values():
                    env[env_var] = "authsome-proxy-managed"
                    logger.debug("Set dummy env var {} for provider {}", env_var, provider.name)

    @staticmethod
    def _build_ca_bundle(server: RunningProxy) -> Path | None:
        """Create a temp file containing system CAs + the mitmproxy CA cert."""
        mitm_ca = server.ca_cert_path
        if not mitm_ca.exists():
            logger.warning("Mitmproxy CA cert not found at {}; HTTPS may fail", mitm_ca)
            return None

        # Find the system CA bundle (certifi is a dependency of requests, so it's guaranteed)
        import certifi

        system_ca_path = Path(certifi.where())

        # Combine system CAs + mitmproxy CA into a temp file
        # We use a unique prefix to avoid collisions if multiple instances run
        fd, name = tempfile.mkstemp(prefix="authsome-ca-", suffix=".pem", text=True)
        os.close(fd)  # Close immediately, we'll use Path.write_text
        path = Path(name)
        try:
            content = system_ca_path.read_text(encoding="utf-8") + "\n" + mitm_ca.read_text(encoding="utf-8")
            path.write_text(content, encoding="utf-8")
        except Exception as e:
            logger.error("Failed to create combined CA bundle: {}", e)
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
            return None

        return path

    @staticmethod
    def _add_ca_to_macos_keychain(ca_cert_path: Path) -> bool:
        """Add the mitmproxy CA to the macOS login keychain.

        Go's crypto/x509 on macOS uses the native Security framework and
        ignores SSL_CERT_FILE, so the only reliable way to make Go binaries
        (gh, terraform, kubectl, …) trust the mitmproxy CA is to add it to
        the login keychain directly.

        Returns True if the cert was newly added (caller must remove it on exit).
        Returns False on non-macOS, if the cert was already present, or if the
        add fails (the subprocess proceeds anyway — TLS errors may still occur).
        """
        if sys.platform != "darwin":
            return False
        if not ca_cert_path.exists():
            return False

        keychain = Path.home() / "Library/Keychains/login.keychain-db"
        if not keychain.exists():
            return False

        # Avoid double-adding: if the user already has a cert with CN=mitmproxy
        # in their keychain (e.g. from a manual mitmproxy install), don't touch it.
        check = subprocess.run(
            ["security", "find-certificate", "-c", "mitmproxy", str(keychain)],
            capture_output=True,
            text=True,
        )
        if check.returncode == 0:
            logger.debug("mitmproxy CA already present in macOS login keychain; skipping add")
            return False

        result = subprocess.run(
            [
                "security",
                "add-trusted-cert",
                "-d",
                "-r",
                "trustRoot",
                "-k",
                str(keychain),
                str(ca_cert_path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            logger.debug("Added mitmproxy CA to macOS login keychain")
            return True

        logger.warning(
            "Could not add mitmproxy CA to macOS login keychain"
            " (Go-based tools like gh/terraform/kubectl may fail with TLS errors): {}",
            result.stderr.strip() or result.stdout.strip(),
        )
        return False

    @staticmethod
    def _remove_ca_from_macos_keychain() -> None:
        """Remove the mitmproxy CA previously added by _add_ca_to_macos_keychain."""
        if sys.platform != "darwin":
            return

        keychain = Path.home() / "Library/Keychains/login.keychain-db"
        try:
            subprocess.run(
                ["security", "delete-certificate", "-c", "mitmproxy", str(keychain)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            logger.debug("Removed mitmproxy CA from macOS login keychain")
        except Exception as exc:
            logger.warning("Could not remove mitmproxy CA from macOS login keychain: {}", exc)

    @staticmethod
    def _merge_no_proxy(existing: str) -> str:
        entries = [item.strip() for item in existing.split(",") if item.strip()]
        for host in ["127.0.0.1", "localhost", "::1"]:
            if host not in entries:
                entries.append(host)
        return ",".join(entries)
