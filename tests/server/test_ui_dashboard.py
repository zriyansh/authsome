from pathlib import Path

from fastapi.testclient import TestClient

from authsome.actors import create_identity, load_private_key
from authsome.actors.proof import create_proof_jwt
from authsome.server.app import create_app


def _auth_header(tmp_path: Path, method: str, path: str, *, handle: str) -> dict[str, str]:
    identity = create_identity(tmp_path, handle)
    token = create_proof_jwt(
        private_key=load_private_key(tmp_path, identity.handle),
        issuer=identity.did,
        subject=identity.handle,
        method=method,
        path_query=path,
        body=b"",
    )
    return {"Authorization": f"PoP {token}"}


def _register_identity(client: TestClient, tmp_path: Path, handle: str) -> None:
    identity = create_identity(tmp_path, handle)
    response = client.post("/identities/register", json={"handle": identity.handle, "did": identity.did})
    assert response.status_code == 200


def test_overview_navigation_shows_applications_connections_and_identity(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))
    monkeypatch.delenv("AUTHSOME_DEPLOYMENT_MODE", raising=False)

    with TestClient(create_app()) as client:
        _register_identity(client, tmp_path, "steady-wisely-boldly-0042")
        response = client.get("/ui/")

    assert response.status_code == 200
    assert "Overview" in response.text
    assert "Applications" in response.text
    assert "Connections" in response.text
    assert "Identity" in response.text


def test_applications_page_renders_provider_catalog(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))
    monkeypatch.delenv("AUTHSOME_DEPLOYMENT_MODE", raising=False)

    with TestClient(create_app()) as client:
        _register_identity(client, tmp_path, "steady-wisely-boldly-0042")
        response = client.get("/ui/applications")

    assert response.status_code == 200
    assert "Applications" in response.text


def test_identity_page_renders_informational_identity_view(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))
    monkeypatch.delenv("AUTHSOME_DEPLOYMENT_MODE", raising=False)

    with TestClient(create_app()) as client:
        _register_identity(client, tmp_path, "steady-wisely-boldly-0042")
        response = client.get("/ui/identity")

    assert response.status_code == 200
    assert "Identity" in response.text
    assert "steady-wisely-boldly-0042" in response.text
