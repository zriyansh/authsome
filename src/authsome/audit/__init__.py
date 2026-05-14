"""Audit models and transitional logging helpers for Authsome operations."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger
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


class AuditLogger:
    """Append-only structured audit logger."""

    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath

    def log(self, event_type: str, **kwargs: Any) -> None:
        """Write an event to the audit log."""

        if not self.filepath.parent.exists():
            try:
                self.filepath.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error("Failed to create audit log directory {}: {}", self.filepath.parent, e)
                return

        filtered_kwargs = {k: v for k, v in kwargs.items() if v is not None}
        event = AuditEvent(
            event=event_type,
            provider=filtered_kwargs.pop("provider", None),
            connection=filtered_kwargs.pop("connection", None),
            identity=filtered_kwargs.pop("identity", None),
            status=filtered_kwargs.pop("status", None),
            metadata=filtered_kwargs,
        )
        entry = {
            "event_id": event.event_id,
            "timestamp": event.timestamp.isoformat(),
            "event": event.event,
            "provider": event.provider,
            "connection": event.connection,
            "identity": event.identity,
            "status": event.status,
            **event.metadata,
        }
        entry = {key: value for key, value in entry.items() if value is not None}

        try:
            with open(self.filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error("Failed to write to audit log at {}: {}", self.filepath, e)


_logger_instance: AuditLogger | None = None
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


def setup(filepath: Path) -> None:
    """Initialize the global audit logger singleton."""
    global _logger_instance, _store_instance
    _logger_instance = AuditLogger(filepath)
    _store_instance = None


def setup_store(store: AppStore) -> None:
    """Initialize daemon-owned audit persistence."""
    global _logger_instance, _store_instance
    _logger_instance = None
    _store_instance = store


def clear() -> None:
    """Reset global audit persistence."""
    global _logger_instance, _store_instance
    _logger_instance = None
    _store_instance = None


async def alog(event_type: str, **kwargs: Any) -> None:
    """Write an event using the configured async sink when available."""
    if _store_instance is not None:
        await _store_instance.append_audit_event(_build_event(event_type, **kwargs))
        return
    log(event_type, **kwargs)


def log(event_type: str, **kwargs: Any) -> None:
    """Write an event to the global audit log."""
    if _logger_instance is not None:
        _logger_instance.log(event_type, **kwargs)
