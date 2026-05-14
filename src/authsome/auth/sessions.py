"""Auth-owned session models and in-memory session store."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from authsome.utils import utc_now

if TYPE_CHECKING:
    from authsome.store.interfaces import AppStore

DEFAULT_SESSION_TTL_SECONDS = 300


class AuthSessionStatus(StrEnum):
    PENDING = "pending"
    WAITING_FOR_USER = "waiting_for_user"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class AuthSession(BaseModel):
    """Internal auth session state.

    This intentionally mirrors the fields existing flow handlers need today
    while moving ownership into the auth package.
    """

    session_id: str
    provider: str
    identity: str
    connection_name: str
    flow_type: str
    state: str = AuthSessionStatus.PENDING
    status_message: str | None = None
    error_message: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime = Field(default_factory=lambda: utc_now() + timedelta(seconds=DEFAULT_SESSION_TTL_SECONDS))

    @property
    def is_expired(self) -> bool:
        return utc_now() >= self.expires_at


class AuthSessionStore:
    """Store-backed auth session state for the daemon process."""

    def __init__(self, store: AppStore) -> None:
        self._store = store

    async def create(
        self,
        *,
        provider: str,
        identity: str,
        connection_name: str,
        flow_type: str,
        ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
    ) -> AuthSession:
        session = AuthSession(
            session_id=f"sess_{uuid.uuid4().hex[:12]}",
            provider=provider,
            identity=identity,
            connection_name=connection_name,
            flow_type=flow_type,
            expires_at=utc_now() + timedelta(seconds=ttl_seconds),
        )
        await self.save(session)
        return session

    async def get(self, session_id: str) -> AuthSession:
        session = await self._store.get_auth_session(session_id)
        if session is None:
            raise KeyError(f"Session not found: {session_id}")
        if session.is_expired:
            session.state = AuthSessionStatus.EXPIRED
            await self.delete(session_id)
            session.state = AuthSessionStatus.EXPIRED
            raise KeyError(f"Session expired: {session_id}")
        return session

    async def save(self, session: AuthSession) -> None:
        session.updated_at = utc_now()
        await self._store.save_auth_session(session)
        oauth_state = session.payload.get("internal_state")
        if oauth_state:
            await self._store.save_auth_session_oauth_state(str(oauth_state), session.session_id)

    async def delete(self, session_id: str) -> None:
        session = await self._store.get_auth_session(session_id)
        if session is not None:
            oauth_state = session.payload.get("internal_state")
            if oauth_state:
                await self._store.delete_auth_session_oauth_state(str(oauth_state))
        await self._store.delete_auth_session(session_id)

    async def index_oauth_state(self, session: AuthSession) -> None:
        oauth_state = session.payload.get("internal_state")
        if oauth_state:
            await self._store.save_auth_session_oauth_state(str(oauth_state), session.session_id)
        await self.save(session)

    async def get_by_oauth_state(self, state: str) -> AuthSession:
        session_id = await self._store.get_auth_session_id_by_state(state)
        if session_id is None:
            raise KeyError(f"Session not found for OAuth state: {state}")
        session = await self.get(session_id)
        if session.is_expired:
            session.state = AuthSessionStatus.EXPIRED
            await self.delete(session.session_id)
            raise KeyError(f"Session expired: {session.session_id}")
        return session
