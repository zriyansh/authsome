from pathlib import Path

from fastapi.testclient import TestClient

from authsome.identity.keys import create_identity
from authsome.server.app import create_app
from tests.server.test_pop_auth import _auth_header


def _register_identity(client: TestClient, tmp_path: Path, handle: str) -> None:
    identity = create_identity(tmp_path, handle)
    response = client.post("/identities/register", json={"handle": identity.handle, "did": identity.did})
    assert response.status_code == 200


def test_hosted_revoke_is_rejected(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))
    monkeypatch.setenv("AUTHSOME_DEPLOYMENT_MODE", "hosted")

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

    with TestClient(create_app()) as client:
        _register_identity(client, tmp_path, "steady-wisely-boldly-0042")
        response = client.delete(
            "/providers/github",
            headers=_auth_header(tmp_path, "DELETE", "/providers/github"),
        )

    assert response.status_code == 400
    assert response.json()["error"] == "OperationNotAllowedError"
    assert response.json()["operation"] == "remove"
