"""Local identity files and did:key helpers."""

from __future__ import annotations

import os
import random
import re
from datetime import UTC, datetime
from pathlib import Path

import base58
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from pydantic import BaseModel, Field

_ED25519_MULTICODEC_PREFIX = b"\xed\x01"
_DID_KEY_PREFIX = "did:key:z"
_HANDLE_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")

_ADJECTIVES = (
    "brisk",
    "calm",
    "clear",
    "eager",
    "fresh",
    "gentle",
    "honest",
    "kind",
    "lively",
    "quiet",
    "rapid",
    "steady",
    "swift",
    "vivid",
)
_ADVERBS = (
    "boldly",
    "brightly",
    "clearly",
    "deeply",
    "easily",
    "firmly",
    "gladly",
    "lightly",
    "quickly",
    "smoothly",
    "warmly",
    "wisely",
)


class IdentityMetadata(BaseModel):
    """Local identity metadata stored beside the caller private key."""

    handle: str
    did: str
    name: str | None = None
    description: str | None = None
    owner_email: str | None = None
    registered: bool = False
    registration_status: str = "local"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {"extra": "allow"}


def identities_dir(home: Path) -> Path:
    return home / "identities"


def identity_metadata_path(home: Path, handle: str) -> Path:
    return identities_dir(home) / f"{handle}.json"


def identity_key_path(home: Path, handle: str) -> Path:
    return identities_dir(home) / f"{handle}.key"


def generate_handle() -> str:
    """Generate a human-readable identity handle."""
    return "-".join(
        (
            random.choice(_ADJECTIVES),
            random.choice(_ADVERBS),
            random.choice(_ADVERBS),
            f"{random.SystemRandom().randint(0, 9999):04d}",
        )
    )


def validate_handle(handle: str) -> str:
    if not _HANDLE_RE.match(handle):
        raise ValueError(f"Invalid identity handle: {handle}")
    return handle


def public_key_to_did_key(public_key: Ed25519PublicKey) -> str:
    raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return _DID_KEY_PREFIX + base58.b58encode(_ED25519_MULTICODEC_PREFIX + raw).decode("ascii")


def public_key_from_did_key(did: str) -> Ed25519PublicKey:
    if not did.startswith(_DID_KEY_PREFIX):
        raise ValueError("Only did:key Ed25519 identifiers are supported")
    try:
        decoded = base58.b58decode(did[len(_DID_KEY_PREFIX) :])
    except ValueError as exc:
        raise ValueError("Malformed did:key value") from exc
    if not decoded.startswith(_ED25519_MULTICODEC_PREFIX):
        raise ValueError("did:key does not use the Ed25519 multicodec prefix")
    raw_key = decoded[len(_ED25519_MULTICODEC_PREFIX) :]
    if len(raw_key) != 32:
        raise ValueError("Ed25519 did:key public key must be 32 bytes")
    return Ed25519PublicKey.from_public_bytes(raw_key)


def private_key_to_hex(private_key: Ed25519PrivateKey) -> str:
    raw = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return raw.hex()


def private_key_from_hex(value: str) -> Ed25519PrivateKey:
    try:
        raw = bytes.fromhex(value.strip())
    except ValueError as exc:
        raise ValueError("Malformed Ed25519 private key hex") from exc
    if len(raw) != 32:
        raise ValueError("Ed25519 private key must be 32 bytes")
    return Ed25519PrivateKey.from_private_bytes(raw)


def load_private_key(home: Path, handle: str) -> Ed25519PrivateKey:
    return private_key_from_hex(identity_key_path(home, handle).read_text(encoding="utf-8"))


def load_identity(home: Path, handle: str) -> IdentityMetadata:
    return IdentityMetadata.model_validate_json(identity_metadata_path(home, handle).read_text(encoding="utf-8"))


def identity_exists(home: Path, handle: str) -> bool:
    return identity_metadata_path(home, handle).exists() and identity_key_path(home, handle).exists()


def create_identity(home: Path, handle: str | None = None) -> IdentityMetadata:
    """Create a local identity and private key, returning existing metadata if present."""
    resolved_handle = validate_handle(handle or _unique_handle(home))
    if identity_exists(home, resolved_handle):
        return load_identity(home, resolved_handle)

    directory = identities_dir(home)
    directory.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(directory, 0o700)
    except OSError:
        pass

    private_key = Ed25519PrivateKey.generate()
    did = public_key_to_did_key(private_key.public_key())
    now = datetime.now(UTC)
    metadata = IdentityMetadata(
        handle=resolved_handle,
        did=did,
        name=resolved_handle,
        created_at=now,
        updated_at=now,
    )

    key_path = identity_key_path(home, resolved_handle)
    metadata_path = identity_metadata_path(home, resolved_handle)
    key_path.write_text(private_key_to_hex(private_key) + "\n", encoding="utf-8")
    try:
        os.chmod(key_path, 0o600)
    except OSError:
        pass
    metadata_path.write_text(metadata.model_dump_json(indent=2), encoding="utf-8")
    return metadata


def remove_legacy_default_identity(home: Path) -> None:
    """Remove legacy local files for the implicit default identity."""
    for path in (identity_metadata_path(home, "default"), identity_key_path(home, "default")):
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def ensure_local_identity(home: Path) -> IdentityMetadata:
    """Ensure a non-default local identity exists."""
    remove_legacy_default_identity(home)
    directory = identities_dir(home)
    if directory.exists():
        for metadata_path in sorted(directory.glob("*.json")):
            handle = metadata_path.stem
            if handle != "default" and identity_exists(home, handle):
                return load_identity(home, handle)
    return create_identity(home)


def _unique_handle(home: Path) -> str:
    for _ in range(100):
        handle = generate_handle()
        if not identity_exists(home, handle):
            return handle
    raise RuntimeError("Unable to generate a unique identity handle")
