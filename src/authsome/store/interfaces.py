"""Unified storage interfaces for Authsome."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from key_value.aio.protocols.key_value import AsyncKeyValue

if TYPE_CHECKING:
    from authsome.audit import AuditEvent
    from authsome.auth.sessions import AuthSession
    from authsome.identity.registry import IdentityRegistration


class AppStore(ABC):
    """Storage backend exposing raw async KV plus daemon-owned records."""

    @property
    @abstractmethod
    def home(self) -> Path:
        """Base directory for this storage system."""
        ...

    @property
    @abstractmethod
    def kv(self) -> AsyncKeyValue:
        """The underlying async key-value store."""
        ...

    # ── Initialization ────────────────────────────────────────────────────

    @abstractmethod
    async def ensure_initialized(self) -> None:
        """Seed the store with version marker and default config."""
        ...

    @abstractmethod
    async def is_healthy(self) -> bool:
        """Check if the store is accessible."""
        ...

    @abstractmethod
    async def check_integrity(self) -> bool:
        """Perform a health check on the storage medium."""
        ...

    # ── Daemon-owned state ────────────────────────────────────────────────

    @abstractmethod
    async def save_identity_registration(self, registration: IdentityRegistration) -> None:
        """Persist an identity registration."""
        ...

    @abstractmethod
    async def get_identity_registration(self, handle: str) -> IdentityRegistration | None:
        """Load a persisted identity registration."""
        ...

    @abstractmethod
    async def list_identity_registrations(self) -> list[IdentityRegistration]:
        """List all persisted identity registrations."""
        ...

    @abstractmethod
    async def get_auth_session(self, session_id: str) -> AuthSession | None:
        """Load an auth session by identifier."""
        ...

    @abstractmethod
    async def save_auth_session(self, session: AuthSession) -> None:
        """Persist an auth session update."""
        ...

    @abstractmethod
    async def save_auth_session_oauth_state(self, state: str, session_id: str) -> None:
        """Persist an OAuth state to session mapping."""
        ...

    @abstractmethod
    async def delete_auth_session(self, session_id: str) -> None:
        """Delete an auth session."""
        ...

    @abstractmethod
    async def get_auth_session_id_by_state(self, state: str) -> str | None:
        """Load a persisted OAuth state to session mapping."""
        ...

    @abstractmethod
    async def delete_auth_session_oauth_state(self, state: str) -> None:
        """Delete a persisted OAuth state to session mapping."""
        ...

    @abstractmethod
    async def append_audit_event(self, event: AuditEvent) -> None:
        """Persist an audit event."""
        ...

    @abstractmethod
    async def list_audit_events(self, *, identity: str | None = None, limit: int = 50) -> list[AuditEvent]:
        """List recent audit events, optionally filtered by identity."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close all underlying storage connections."""
        ...
