"""Tests for daemon-owned audit routes."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from authsome.identity.keys import create_identity, load_private_key
from authsome.identity.proof import create_proof_jwt
from authsome.server.app import create_app


def _auth_header(tmp_path: Path, method: str, path: str, *, handle: str, body: bytes = b"") -> dict[str, str]:
    identity = create_identity(tmp_path, handle)
    token = create_proof_jwt(
        private_key=load_private_key(tmp_path, identity.handle),
        issuer=identity.did,
        subject=identity.handle,
        method=method,
        path_query=path,
        body=body,
    )
    return {"Authorization": f"PoP {token}"}


def test_audit_event_can_be_submitted_and_listed(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))
    identity = create_identity(tmp_path, "steady-wisely-boldly-0042")
    other_identity = create_identity(tmp_path, "rapid-brightly-firmly-0007")

    with TestClient(create_app()) as client:
        registration = client.post("/identities/register", json={"handle": identity.handle, "did": identity.did})
        assert registration.status_code == 200
        other_registration = client.post(
            "/identities/register",
            json={"handle": other_identity.handle, "did": other_identity.did},
        )
        assert other_registration.status_code == 200

        body = json.dumps(
            {
                "event": "login",
                "provider": "github",
                "connection": "default",
                "identity": other_identity.handle,
            },
            separators=(",", ":"),
        ).encode("utf-8")
        submit = client.post(
            "/audit/events",
            content=body,
            headers={
                "Content-Type": "application/json",
                **_auth_header(tmp_path, "POST", "/audit/events", handle=identity.handle, body=body),
            },
        )
        assert submit.status_code == 202
        assert submit.json() == {"status": "accepted"}

        listed = client.get(
            "/audit/events?limit=10",
            headers=_auth_header(tmp_path, "GET", "/audit/events?limit=10", handle=identity.handle),
        )
        assert listed.status_code == 200
        payload = listed.json()
        assert [event["event"] for event in payload["events"]] == ["login"]
        assert [event["identity"] for event in payload["events"]] == [identity.handle]

        other_listed = client.get(
            "/audit/events?limit=10",
            headers=_auth_header(tmp_path, "GET", "/audit/events?limit=10", handle=other_identity.handle),
        )
        assert other_listed.status_code == 200
        assert other_listed.json()["events"] == []
