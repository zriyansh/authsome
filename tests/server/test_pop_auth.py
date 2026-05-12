from pathlib import Path

from fastapi.testclient import TestClient

from authsome.identity.keys import create_identity, load_private_key
from authsome.identity.proof import create_proof_jwt
from authsome.server.app import create_app


def _auth_header(tmp_path: Path, method: str, path: str, body: bytes = b"") -> dict[str, str]:
    identity = create_identity(tmp_path, "steady-wisely-boldly-0042")
    token = create_proof_jwt(
        private_key=load_private_key(tmp_path, identity.handle),
        issuer=identity.did,
        subject=identity.handle,
        method=method,
        path_query=path,
        body=body,
    )
    return {"Authorization": f"PoP {token}"}


def test_whoami_requires_pop(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))

    with TestClient(create_app()) as client:
        response = client.get("/whoami")

    assert response.status_code == 401


def test_whoami_accepts_valid_pop_and_scopes_identity(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))

    with TestClient(create_app()) as client:
        response = client.get("/whoami", headers=_auth_header(tmp_path, "GET", "/whoami"))

    assert response.status_code == 200
    assert response.json()["identity"] == "steady-wisely-boldly-0042"
    assert response.json()["did"].startswith("did:key:z6Mk")


def test_whoami_rejects_wrong_path_claim(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))

    with TestClient(create_app()) as client:
        response = client.get("/whoami", headers=_auth_header(tmp_path, "GET", "/connections"))

    assert response.status_code == 401
