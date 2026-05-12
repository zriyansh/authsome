"""Local identity helpers."""

from __future__ import annotations

from dataclasses import dataclass
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
    public_key_from_did_key,
    public_key_to_did_key,
    remove_legacy_default_identity,
)

DEFAULT_IDENTITY = "default"


@dataclass(frozen=True)
class Identity:
    """The current local identity."""

    name: str = DEFAULT_IDENTITY


def current() -> Identity:
    """Return the current local identity."""
    return Identity()


async def current_from_home(home: Path) -> IdentityMetadata:
    """Return the configured local identity, bootstrapping it if needed."""
    from authsome.store.local import LocalAppStore

    store = LocalAppStore(home)
    await store.ensure_initialized()
    config = await store.get_config()
    await store.save_config(config)
    return ensure_local_identity(home)


__all__ = [
    "DEFAULT_IDENTITY",
    "Identity",
    "IdentityMetadata",
    "create_identity",
    "current",
    "current_from_home",
    "ensure_local_identity",
    "identities_dir",
    "identity_exists",
    "identity_key_path",
    "identity_metadata_path",
    "load_identity",
    "load_private_key",
    "public_key_from_did_key",
    "public_key_to_did_key",
    "remove_legacy_default_identity",
]
