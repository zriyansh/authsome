"""Local identity helpers."""

from __future__ import annotations

from pathlib import Path

from authsome.identity.keys import (
    IdentityMetadata,
    create_identity,
    ensure_local_identity,
    identities_dir,
    identity_exists,
    identity_key_path,
    identity_metadata_path,
    load_identity,
    load_private_key,
    mark_registered,
    public_key_from_did_key,
    public_key_to_did_key,
    remove_legacy_default_identity,
)


async def current_from_home(home: Path) -> IdentityMetadata:
    """Return the configured local identity, bootstrapping it if needed."""
    from authsome.store.local import LocalAppStore

    store = LocalAppStore(home)
    await store.ensure_initialized()
    config = await store.get_config()
    return ensure_local_identity(home, active_handle=config.active_identity)


__all__ = [
    "IdentityMetadata",
    "create_identity",
    "current_from_home",
    "ensure_local_identity",
    "identities_dir",
    "identity_exists",
    "identity_key_path",
    "identity_metadata_path",
    "load_identity",
    "load_private_key",
    "mark_registered",
    "public_key_from_did_key",
    "public_key_to_did_key",
    "remove_legacy_default_identity",
]
