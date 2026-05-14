"""Server-owned identity registry."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from authsome.identity.keys import public_key_from_did_key, validate_handle

if TYPE_CHECKING:
    from authsome.store.interfaces import AppStore


class IdentityRegistration(BaseModel):
    """Registered identity binding stored by the daemon."""

    handle: str
    did: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class IdentityRegistrationError(ValueError):
    """Raised when an identity registration conflicts with existing registry state."""


class IdentityRegistry:
    """Store-backed authoritative registry for daemon identity handles."""

    def __init__(self, store: AppStore) -> None:
        self._store = store

    async def register(self, *, handle: str, did: str) -> IdentityRegistration:
        """Register a handle/DID binding, idempotent only for the same pair."""
        handle = validate_handle(handle)
        public_key_from_did_key(did)

        existing = await self._store.get_identity_registration(handle)
        if existing is not None:
            if existing.did == did:
                return existing
            raise IdentityRegistrationError(f"Identity handle '{handle}' is already registered")

        for registration in await self._store.list_identity_registrations():
            if registration.did == did:
                raise IdentityRegistrationError(f"DID is already registered to identity handle '{registration.handle}'")

        now = datetime.now(UTC)
        registration = IdentityRegistration(handle=handle, did=did, created_at=now, updated_at=now)
        await self._store.save_identity_registration(registration)
        return registration

    async def resolve(self, handle: str) -> IdentityRegistration | None:
        return await self._store.get_identity_registration(handle)

    async def list_handles(self) -> list[str]:
        """Return all registered identity handles."""
        registrations = await self._store.list_identity_registrations()
        return sorted(registration.handle for registration in registrations)
