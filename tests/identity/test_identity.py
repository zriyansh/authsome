from pathlib import Path

import pytest

from authsome.identity import current_from_home
from authsome.identity.keys import (
    create_identity,
    identity_key_path,
    public_key_from_did_key,
    public_key_to_did_key,
)


@pytest.mark.asyncio
async def test_current_from_home_replaces_legacy_default(tmp_path: Path) -> None:
    identity = await current_from_home(tmp_path)

    assert identity.handle != "default"
    assert identity.did.startswith("did:key:z6Mk")
    assert len(identity.handle.split("-")) == 4


def test_create_identity_writes_private_key_mode_0600(tmp_path: Path) -> None:
    identity = create_identity(tmp_path, "steady-wisely-boldly-0042")
    key_path = identity_key_path(tmp_path, identity.handle)

    assert key_path.exists()
    assert key_path.stat().st_mode & 0o777 == 0o600


def test_did_key_roundtrip(tmp_path: Path) -> None:
    identity = create_identity(tmp_path, "steady-wisely-boldly-0042")
    public_key = public_key_from_did_key(identity.did)

    assert public_key_to_did_key(public_key) == identity.did


def test_invalid_did_key_rejected() -> None:
    with pytest.raises(ValueError, match="Only did:key"):
        public_key_from_did_key("did:web:example.com")
