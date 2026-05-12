"""Local identity helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from authsome.identity.keys import (
    IdentityMetadata,
    create_identity,
    ensure_default_identity,
    identities_dir,
    identity_exists,
    identity_key_path,
    identity_metadata_path,
    load_identity,
    load_private_key,
    public_key_from_did_key,
    public_key_to_did_key,
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
    original_default = config.default_profile
    config, identity = await ensure_default_identity(home, config)
    if config.default_profile != original_default:
        await store.save_config(config)
    return identity


__all__ = [
    "DEFAULT_IDENTITY",
    "Identity",
    "IdentityMetadata",
    "create_identity",
    "current",
    "current_from_home",
    "ensure_default_identity",
    "identities_dir",
    "identity_exists",
    "identity_key_path",
    "identity_metadata_path",
    "load_identity",
    "load_private_key",
    "public_key_from_did_key",
    "public_key_to_did_key",
]
