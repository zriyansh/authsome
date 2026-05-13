"""Local disk-backed implementation of the AppStore."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from key_value.aio.protocols.key_value import AsyncKeyValue
from key_value.aio.stores.disk import DiskStore
from loguru import logger

from authsome.auth.models.config import GlobalConfig
from authsome.store.interfaces import AppStore


class LocalAppStore(AppStore):
    """Disk-backed AppStore using py-key-value-aio's DiskStore.

    All data lives inside a single ``kv_store/`` directory managed by
    diskcache.  Swapping to a remote backend (e.g. PostgresStore)
    requires only replacing the DiskStore constructor call.
    """

    def __init__(self, home_dir: Path) -> None:
        self._home = home_dir
        self._home.mkdir(parents=True, exist_ok=True)
        self._server_home = self._home / "server"
        self._server_home.mkdir(parents=True, exist_ok=True)
        self._store = DiskStore(directory=str(self._server_home / "kv_store"))

    @property
    def home(self) -> Path:
        return self._home

    @property
    def server_home(self) -> Path:
        return self._server_home

    @property
    def kv(self) -> AsyncKeyValue:
        return self._store

    # ── Initialization ────────────────────────────────────────────────────

    async def ensure_initialized(self) -> None:
        _ensure_macos_keychain_ca()
        if await self._store.get("version", collection="config") is not None:
            config = await self.get_config()
            await self.save_config(config)
            return
        await self._store.put("version", {"data": "1"}, collection="config")
        await self.save_config(GlobalConfig())

    async def is_healthy(self) -> bool:
        return True

    async def check_integrity(self) -> bool:
        return True

    # ── Config (unencrypted) ──────────────────────────────────────────────

    async def get_config(self) -> GlobalConfig:
        val = await self._store.get("global", collection="config")
        if not val:
            return GlobalConfig()
        try:
            return GlobalConfig.model_validate_json(val["data"])
        except Exception as exc:
            logger.warning("Failed to parse config, using defaults: {}", exc)
            return GlobalConfig()

    async def save_config(self, config: GlobalConfig) -> None:
        data = config.model_dump(mode="json")
        await self._store.put("global", {"data": json.dumps(data, indent=2)}, collection="config")

    async def close(self) -> None:
        pass


def _ensure_macos_keychain_ca() -> None:
    """Ensure the mitmproxy CA is generated and trusted in the macOS login keychain.

    Go's crypto/x509 on macOS uses the native Security framework and
    ignores SSL_CERT_FILE, so the only reliable way to make Go binaries
    (gh, terraform, kubectl, …) trust the mitmproxy CA is to add it to
    the login keychain directly.

    The certificate is added persistently once to avoid repeated OS password
    prompts. It will skip addition on subsequent calls if already present.
    """
    if sys.platform != "darwin":
        return

    keychain = Path.home() / "Library/Keychains/login.keychain-db"
    if not keychain.exists():
        return

    # Avoid double-adding: if the user already has a cert with CN=mitmproxy
    # in their keychain (e.g. from a manual mitmproxy install), don't touch it.
    check = subprocess.run(
        ["security", "find-certificate", "-c", "mitmproxy", str(keychain)],
        capture_output=True,
        text=True,
    )
    if check.returncode == 0:
        logger.debug("mitmproxy CA already present in macOS login keychain; skipping add")
        return

    # Ensure CA certificate is generated so we can register it
    confdir = Path.home() / ".mitmproxy"
    ca_cert_path = confdir / "mitmproxy-ca-cert.pem"
    if not ca_cert_path.exists():
        try:
            from mitmproxy.certs import CertStore

            CertStore.from_store(confdir, "mitmproxy", 2048)
            logger.debug("Generated mitmproxy CA certificate at {}", ca_cert_path)
        except Exception as e:
            logger.debug("Failed to generate mitmproxy CA certificate: {}", e)
            return

    if not ca_cert_path.exists():
        return

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
        return

    logger.warning(
        "Could not add mitmproxy CA to macOS login keychain"
        " (Go-based tools like gh/terraform/kubectl may fail with TLS errors): {}",
        result.stderr.strip() or result.stdout.strip(),
    )
