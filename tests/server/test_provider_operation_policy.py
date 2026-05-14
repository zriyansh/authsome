import json
from pathlib import Path

from fastapi.testclient import TestClient

from authsome.identity.keys import create_identity
from authsome.server import dependencies
from authsome.server.app import create_app
from authsome.store.local import LocalAppStore
from tests.server.test_pop_auth import _auth_header


def _register_identity(client: TestClient, tmp_path: Path, handle: str) -> None:
    identity = create_identity(tmp_path, handle)
    response = client.post("/identities/register", json={"handle": identity.handle, "did": identity.did})
    assert response.status_code == 200


def test_hosted_revoke_is_rejected(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))
    monkeypatch.setenv("AUTHSOME_DEPLOYMENT_MODE", "hosted")
    monkeypatch.setenv("AUTHSOME_POSTGRES_URL", "postgresql://authsome:secret@db/authsome")
    monkeypatch.setattr(dependencies, "PostgresAppStore", lambda home, _url: LocalAppStore(home))

    with TestClient(create_app()) as client:
        _register_identity(client, tmp_path, "steady-wisely-boldly-0042")
        response = client.post(
            "/connections/github/revoke",
            headers=_auth_header(tmp_path, "POST", "/connections/github/revoke"),
        )

    assert response.status_code == 400
    assert response.json()["error"] == "OperationNotAllowedError"
    assert response.json()["operation"] == "revoke"


def test_hosted_remove_is_rejected(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))
    monkeypatch.setenv("AUTHSOME_DEPLOYMENT_MODE", "hosted")
    monkeypatch.setenv("AUTHSOME_POSTGRES_URL", "postgresql://authsome:secret@db/authsome")
    monkeypatch.setattr(dependencies, "PostgresAppStore", lambda home, _url: LocalAppStore(home))

    with TestClient(create_app()) as client:
        _register_identity(client, tmp_path, "steady-wisely-boldly-0042")
        response = client.delete(
            "/providers/github",
            headers=_auth_header(tmp_path, "DELETE", "/providers/github"),
        )

    assert response.status_code == 400
    assert response.json()["error"] == "OperationNotAllowedError"
    assert response.json()["operation"] == "remove"


def test_hosted_register_provider_is_rejected(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))
    monkeypatch.setenv("AUTHSOME_DEPLOYMENT_MODE", "hosted")
    payload = {
        "definition": {
            "name": "custom-api",
            "display_name": "Custom API",
            "auth_type": "api_key",
            "flow": "api_key",
            "api_key": {"header_name": "Authorization"},
        }
    }
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    with TestClient(create_app()) as client:
        _register_identity(client, tmp_path, "steady-wisely-boldly-0042")
        response = client.post(
            "/providers",
            content=body,
            headers={
                **_auth_header(tmp_path, "POST", "/providers", body=body),
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 400
    assert response.json()["error"] == "OperationNotAllowedError"
    assert response.json()["operation"] == "register"
