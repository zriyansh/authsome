"""Concrete local dependency wiring for the daemon server."""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from authsome.auth import AuthService

from authsome.identity import current_from_home
from authsome.identity.registry import IdentityRegistry
from authsome.server.urls import build_server_base_url
from authsome.store.local import LocalAppStore
from authsome.vault import Vault


def get_authsome_home() -> Path:
    """Return the local Authsome home directory."""
    return Path(os.environ.get("AUTHSOME_HOME", str(Path.home() / ".authsome")))


def get_server_home(home: Path | None = None) -> Path:
    """Return the daemon-owned state directory."""
    return (home or get_authsome_home()) / "server"


def get_ui_session_secret_path(home: Path | None = None) -> Path:
    """Return the hosted UI session signing-secret path."""
    return get_server_home(home) / "ui_session_secret.key"


def get_server_base_url() -> str:
    """Return the daemon's canonical external base URL."""
    return build_server_base_url()


def get_deployment_mode() -> str:
    """Return the daemon deployment mode."""
    mode = os.environ.get("AUTHSOME_DEPLOYMENT_MODE", "local").strip().lower()
    return "hosted" if mode == "hosted" else "local"


def list_registered_identity_handles(home: Path | None = None) -> list[str]:
    """Return identity handles registered with this daemon."""
    registry = IdentityRegistry(get_server_home(home))
    return registry.list_handles()


def load_ui_session_signing_secret(home: Path | None = None) -> str:
    """Load or create the hosted UI session signing secret."""
    path = get_ui_session_secret_path(home)
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        path.parent.mkdir(parents=True, exist_ok=True)
        secret = secrets.token_hex(32)
        path.write_text(secret, encoding="utf-8")
        os.chmod(path, 0o600)
        return secret


async def get_local_ui_identity(home: Path | None = None) -> str:
    """Resolve the local active identity handle for the server-rendered UI."""
    identity = await current_from_home(home or get_authsome_home())
    return identity.handle


async def create_vault(home: Path | None = None) -> Vault:
    """Create the daemon vault without requiring caller identity files."""
    from authsome import audit

    resolved_home = home or get_authsome_home()
    audit.setup(resolved_home / "audit.log")
    app_store = LocalAppStore(resolved_home)
    await app_store.ensure_initialized()

    config = await app_store.get_config()
    crypto_mode = config.encryption.mode if config.encryption else "local_key"
    return Vault(
        app_store=app_store,
        crypto_mode=crypto_mode,
        master_key_path=get_server_home(resolved_home) / "master.key",
    )


async def create_auth_service(home: Path | None = None, identity: str | None = None) -> AuthService:
    """Create an auth service scoped to an identity handle."""
    from authsome.auth import AuthService

    if not identity:
        raise ValueError("create_auth_service requires an explicit identity handle")
    vault = await create_vault(home)
    return AuthService(vault=vault, identity=identity, deployment_mode=get_deployment_mode())
