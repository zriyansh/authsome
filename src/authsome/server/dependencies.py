"""Concrete local dependency wiring for the daemon server."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from authsome.auth import AuthService
    from authsome.store.interfaces import AppStore

from authsome.identity.registry import IdentityRegistry
from authsome.server.urls import build_server_base_url
from authsome.store.local import LocalAppStore
from authsome.store.postgresql import PostgresAppStore
from authsome.vault import Vault


def get_authsome_home() -> Path:
    """Return the local Authsome home directory."""
    return Path(os.environ.get("AUTHSOME_HOME", str(Path.home() / ".authsome")))


def get_server_home(home: Path | None = None) -> Path:
    """Return the daemon-owned state directory."""
    return (home or get_authsome_home()) / "server"


def get_server_base_url() -> str:
    """Return the daemon's canonical external base URL."""
    return build_server_base_url()


def get_deployment_mode() -> str:
    """Return the daemon deployment mode."""
    mode = os.environ.get("AUTHSOME_DEPLOYMENT_MODE", "local").strip().lower()
    return "hosted" if mode == "hosted" else "local"


def get_postgres_url() -> str:
    """Return the hosted PostgreSQL connection URL."""
    return os.environ["AUTHSOME_POSTGRES_URL"].strip()


def get_encryption_mode() -> str:
    """Return the vault encryption backend mode."""
    return os.environ.get("AUTHSOME_ENCRYPTION_MODE", "local_key").strip() or "local_key"


async def create_app_store(home: Path | None = None) -> AppStore:
    """Create the daemon application store."""
    resolved_home = home or get_authsome_home()
    if get_deployment_mode() == "hosted":
        app_store = PostgresAppStore(resolved_home, get_postgres_url())
    else:
        app_store = LocalAppStore(resolved_home)
    await app_store.ensure_initialized()
    return app_store


async def list_registered_identity_handles(home: Path | None = None) -> list[str]:
    """Return identity handles registered with this daemon."""
    store = await create_app_store(home)
    try:
        registry = IdentityRegistry(store)
        return await registry.list_handles()
    finally:
        await store.close()


async def create_vault(app_store: AppStore) -> Vault:
    """Create the daemon vault from an initialized application store."""
    resolved_home = app_store.home
    return Vault(
        app_store=app_store,
        crypto_mode=get_encryption_mode(),
        master_key_path=get_server_home(resolved_home) / "master.key",
    )


async def create_auth_service(home: Path | None = None, identity: str | None = None) -> AuthService:
    """Create an auth service scoped to an identity handle."""
    from authsome.auth import AuthService

    if not identity:
        raise ValueError("create_auth_service requires an explicit identity handle")
    store = await create_app_store(home)
    vault = await create_vault(store)
    return AuthService(vault=vault, identity=identity, deployment_mode=get_deployment_mode())
