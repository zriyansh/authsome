"""Tests for daemon audit event models."""

from authsome.audit import AuditEvent


def test_audit_event_captures_known_fields() -> None:
    event = AuditEvent(
        event="login",
        provider="github",
        connection="default",
        identity="steady-wisely-boldly-0042",
        status="success",
    )

    assert event.event == "login"
    assert event.provider == "github"
    assert event.connection == "default"
    assert event.identity == "steady-wisely-boldly-0042"
    assert event.status == "success"


def test_audit_event_metadata_defaults_to_empty_mapping() -> None:
    event = AuditEvent(event="proxy_miss")

    assert event.metadata == {}
    payload = event.model_dump(mode="json")
    assert payload["event"] == "proxy_miss"
    assert "timestamp" in payload
