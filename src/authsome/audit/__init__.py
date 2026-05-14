"""Audit models and transitional logging helpers for Authsome operations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from authsome.utils import utc_now

if TYPE_CHECKING:
    from authsome.store.interfaces import AppStore


class AuditEvent(BaseModel):
    """Structured audit event stored by the daemon."""

    event_id: str = Field(default_factory=lambda: f"audit_{uuid.uuid4().hex}")
    timestamp: datetime = Field(default_factory=utc_now)
    event: str
    provider: str | None = None
    connection: str | None = None
    identity: str | None = None
    status: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


_store_instance: AppStore | None = None


def _build_event(event_type: str, **kwargs: Any) -> AuditEvent:
    filtered_kwargs = {k: v for k, v in kwargs.items() if v is not None}
    return AuditEvent(
        event=event_type,
        provider=filtered_kwargs.pop("provider", None),
        connection=filtered_kwargs.pop("connection", None),
        identity=filtered_kwargs.pop("identity", None),
        status=filtered_kwargs.pop("status", None),
        metadata=filtered_kwargs,
    )


async def alog(event_type: str, **kwargs: Any) -> None:
    """Write an event using the configured async sink when available."""
    if _store_instance is not None:
        await _store_instance.append_audit_event(_build_event(event_type, **kwargs))
        return
