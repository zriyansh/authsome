"""Local disk-backed implementation of the AppStore."""

from __future__ import annotations

import json
from pathlib import Path

from key_value.aio.protocols.key_value import AsyncKeyValue
from key_value.aio.stores.disk import DiskStore

from authsome.audit import AuditEvent
from authsome.auth.sessions import AuthSession
from authsome.identity.registry import IdentityRegistration
from authsome.store.interfaces import AppStore

_CONFIG_COLLECTION = "config"
_IDENTITY_COLLECTION = "daemon:identities"
_IDENTITY_INDEX_KEY = "__index__"
_SESSION_COLLECTION = "daemon:auth_sessions"
_SESSION_INDEX_KEY = "__index__"
_SESSION_STATE_COLLECTION = "daemon:auth_session_states"
_AUDIT_COLLECTION = "daemon:audit"
_AUDIT_INDEX_KEY = "__index__"


class LocalAppStore(AppStore):
    """Disk-backed AppStore using py-key-value-aio's DiskStore.

    All data lives inside a single ``kv_store/`` directory managed by
    diskcache.  Swapping to a remote backend (e.g. PostgresStore)
    requires only replacing the DiskStore constructor call.
    """

    def __init__(self, home_dir: Path) -> None:
        self._home = home_dir
        self._home.mkdir(parents=True, exist_ok=True)
        self._server_home = self._home / "server"
        self._server_home.mkdir(parents=True, exist_ok=True)
        self._store = DiskStore(directory=str(self._server_home / "kv_store"))

    @property
    def home(self) -> Path:
        return self._home

    @property
    def server_home(self) -> Path:
        return self._server_home

    @property
    def kv(self) -> AsyncKeyValue:
        return self._store

    # ── Initialization ────────────────────────────────────────────────────

    async def ensure_initialized(self) -> None:
        if await self._store.get("version", collection=_CONFIG_COLLECTION) is not None:
            return
        await self._store.put("version", {"data": "1"}, collection=_CONFIG_COLLECTION)

    async def is_healthy(self) -> bool:
        return True

    async def check_integrity(self) -> bool:
        return True

    async def save_identity_registration(self, registration: IdentityRegistration) -> None:
        await self._store.put(
            registration.handle,
            registration.model_dump(mode="json"),
            collection=_IDENTITY_COLLECTION,
        )
        await self._append_index(_IDENTITY_COLLECTION, _IDENTITY_INDEX_KEY, registration.handle)

    async def get_identity_registration(self, handle: str) -> IdentityRegistration | None:
        raw = await self._store.get(handle, collection=_IDENTITY_COLLECTION)
        if raw is None:
            return None
        return IdentityRegistration.model_validate(raw)

    async def list_identity_registrations(self) -> list[IdentityRegistration]:
        handles = await self._read_index(_IDENTITY_COLLECTION, _IDENTITY_INDEX_KEY)
        registrations: list[IdentityRegistration] = []
        for handle in handles:
            registration = await self.get_identity_registration(handle)
            if registration is not None:
                registrations.append(registration)
        return registrations

    async def get_auth_session(self, session_id: str) -> AuthSession | None:
        raw = await self._store.get(session_id, collection=_SESSION_COLLECTION)
        if raw is None:
            return None
        return AuthSession.model_validate(raw)

    async def save_auth_session(self, session: AuthSession) -> None:
        await self._store.put(
            session.session_id,
            session.model_dump(mode="json"),
            collection=_SESSION_COLLECTION,
        )
        await self._append_index(_SESSION_COLLECTION, _SESSION_INDEX_KEY, session.session_id)

    async def save_auth_session_oauth_state(self, state: str, session_id: str) -> None:
        await self._store.put(
            state,
            {"session_id": session_id},
            collection=_SESSION_STATE_COLLECTION,
        )

    async def get_auth_session_id_by_state(self, state: str) -> str | None:
        mapping = await self._store.get(state, collection=_SESSION_STATE_COLLECTION)
        if mapping is None:
            return None
        session_id = mapping.get("session_id")
        return session_id if isinstance(session_id, str) else None

    async def delete_auth_session_oauth_state(self, state: str) -> None:
        await self._store.delete(state, collection=_SESSION_STATE_COLLECTION)

    async def delete_auth_session(self, session_id: str) -> None:
        await self._store.delete(session_id, collection=_SESSION_COLLECTION)

    async def append_audit_event(self, event: AuditEvent) -> None:
        await self._store.put(
            event.event_id,
            event.model_dump(mode="json"),
            collection=_AUDIT_COLLECTION,
        )
        await self._append_index(_AUDIT_COLLECTION, _AUDIT_INDEX_KEY, event.event_id)

    async def list_audit_events(self, *, identity: str | None = None, limit: int = 50) -> list[AuditEvent]:
        event_ids = await self._read_index(_AUDIT_COLLECTION, _AUDIT_INDEX_KEY)
        events: list[AuditEvent] = []
        for event_id in reversed(event_ids):
            raw = await self._store.get(event_id, collection=_AUDIT_COLLECTION)
            if raw is not None:
                event = AuditEvent.model_validate(raw)
                if identity is not None and event.identity != identity:
                    continue
                events.append(event)
                if len(events) >= limit:
                    break
        return events

    async def close(self) -> None:
        close = getattr(self._store, "close", None)
        if callable(close):
            await close()

    async def _read_index(self, collection: str, key: str) -> list[str]:
        raw = await self._store.get(key, collection=collection)
        if raw is None:
            return []

        data = raw.get("data")
        if not isinstance(data, str):
            return []

        try:
            values = json.loads(data)
        except json.JSONDecodeError:
            return []
        if not isinstance(values, list):
            return []
        return [value for value in values if isinstance(value, str)]

    async def _append_index(self, collection: str, key: str, value: str) -> None:
        values = await self._read_index(collection, key)
        if value in values:
            return
        values.append(value)
        await self._store.put(key, {"data": json.dumps(values)}, collection=collection)
