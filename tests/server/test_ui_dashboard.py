import asyncio
from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from authsome.actors import create_identity, load_private_key
from authsome.actors.proof import create_proof_jwt
from authsome.auth.models.connection import ConnectionRecord, ProviderMetadataRecord
from authsome.auth.models.enums import AuthType, ConnectionStatus
from authsome.server.app import create_app
from authsome.utils import build_store_key, utc_now


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


def _seed_connection(
    client: TestClient,
    *,
    identity: str,
    provider: str,
    auth_type: AuthType,
    connection_name: str = "default",
    access_token: str | None = None,
    refresh_token: str | None = None,
    api_key: str | None = None,
) -> None:
    resolved = asyncio.run(client.app.state.ownership_resolver.resolve(identity=identity))
    record = ConnectionRecord(
        provider=provider,
        identity=identity,
        principal_id=resolved.principal_id,
        vault_id=resolved.vault_id,
        connection_name=connection_name,
        auth_type=auth_type,
        status=ConnectionStatus.CONNECTED,
        access_token=access_token,
        refresh_token=refresh_token,
        api_key=api_key,
        expires_at=utc_now() + timedelta(hours=1),
    )
    asyncio.run(
        client.app.state.vault.put(
            build_store_key(
                vault=resolved.vault_id,
                provider=provider,
                record_type="connection",
                connection=connection_name,
            ),
            record.model_dump_json(),
            collection=f"vault:{resolved.vault_id}",
        )
    )
    asyncio.run(
        client.app.state.vault.put(
            build_store_key(vault=resolved.vault_id, provider=provider, record_type="metadata"),
            ProviderMetadataRecord(
                identity=identity,
                principal_id=resolved.principal_id,
                vault_id=resolved.vault_id,
                provider=provider,
                connection_names=[connection_name],
                default_connection=connection_name,
                last_used_connection=connection_name,
            ).model_dump_json(),
            collection=f"vault:{resolved.vault_id}",
        )
    )


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


def test_applications_page_shows_provider_login_action(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))
    monkeypatch.delenv("AUTHSOME_DEPLOYMENT_MODE", raising=False)

    with TestClient(create_app()) as client:
        _register_identity(client, tmp_path, "steady-wisely-boldly-0042")
        response = client.get("/ui/applications")

    assert response.status_code == 200
    assert 'action="/ui/apps/github/connect"' in response.text
    assert "Login" in response.text


def test_identity_page_renders_informational_identity_view(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))
    monkeypatch.delenv("AUTHSOME_DEPLOYMENT_MODE", raising=False)

    with TestClient(create_app()) as client:
        _register_identity(client, tmp_path, "steady-wisely-boldly-0042")
        response = client.get("/ui/identity")

    assert response.status_code == 200
    assert "Identity" in response.text
    assert "steady-wisely-boldly-0042" in response.text


def test_provider_page_shows_provider_configuration_not_connection_tokens(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))
    monkeypatch.delenv("AUTHSOME_DEPLOYMENT_MODE", raising=False)

    with TestClient(create_app()) as client:
        _register_identity(client, tmp_path, "steady-wisely-boldly-0042")
        _seed_connection(
            client,
            identity="steady-wisely-boldly-0042",
            provider="github",
            auth_type=AuthType.OAUTH2,
            access_token="gh-access-token",
            refresh_token="gh-refresh-token",
        )
        response = client.get("/ui/apps/github")

    assert response.status_code == 200
    assert "OAuth Application" in response.text or "Managed by Authsome" in response.text
    assert "Access Token" not in response.text


def test_named_connection_detail_route_exists(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))
    monkeypatch.delenv("AUTHSOME_DEPLOYMENT_MODE", raising=False)

    with TestClient(create_app()) as client:
        _register_identity(client, tmp_path, "steady-wisely-boldly-0042")
        _seed_connection(
            client,
            identity="steady-wisely-boldly-0042",
            provider="github",
            auth_type=AuthType.OAUTH2,
            access_token="gh-access-token",
            refresh_token="gh-refresh-token",
        )
        response = client.get("/ui/apps/github/connections/default")

    assert response.status_code == 200


def test_named_connection_detail_page_shows_oauth_tokens(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))
    monkeypatch.delenv("AUTHSOME_DEPLOYMENT_MODE", raising=False)

    with TestClient(create_app()) as client:
        _register_identity(client, tmp_path, "steady-wisely-boldly-0042")
        _seed_connection(
            client,
            identity="steady-wisely-boldly-0042",
            provider="github",
            auth_type=AuthType.OAUTH2,
            access_token="gh-access-token",
            refresh_token="gh-refresh-token",
        )
        response = client.get("/ui/apps/github/connections/default")

    assert response.status_code == 200
    assert "Access Token" in response.text
    assert "Refresh Token" in response.text


def test_named_connection_detail_page_shows_api_key(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))
    monkeypatch.delenv("AUTHSOME_DEPLOYMENT_MODE", raising=False)

    with TestClient(create_app()) as client:
        _register_identity(client, tmp_path, "steady-wisely-boldly-0042")
        _seed_connection(
            client,
            identity="steady-wisely-boldly-0042",
            provider="openai",
            auth_type=AuthType.API_KEY,
            api_key="sk-test-key",
        )
        response = client.get("/ui/apps/openai/connections/default")

    assert response.status_code == 200
    assert "API Credentials" in response.text


def test_provider_page_for_api_key_provider_omits_provider_setup_section(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))
    monkeypatch.delenv("AUTHSOME_DEPLOYMENT_MODE", raising=False)

    with TestClient(create_app()) as client:
        _register_identity(client, tmp_path, "steady-wisely-boldly-0042")
        _seed_connection(
            client,
            identity="steady-wisely-boldly-0042",
            provider="openai",
            auth_type=AuthType.API_KEY,
            api_key="sk-test-key",
        )
        response = client.get("/ui/apps/openai")

    assert response.status_code == 200
    assert "OAuth Application" not in response.text
    assert "API Credentials" not in response.text


def test_provider_page_lists_existing_connections_as_read_only_context(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))
    monkeypatch.delenv("AUTHSOME_DEPLOYMENT_MODE", raising=False)

    with TestClient(create_app()) as client:
        _register_identity(client, tmp_path, "steady-wisely-boldly-0042")
        _seed_connection(
            client,
            identity="steady-wisely-boldly-0042",
            provider="github",
            auth_type=AuthType.OAUTH2,
            access_token="gh-access-token",
            refresh_token="gh-refresh-token",
        )
        response = client.get("/ui/apps/github")

    assert response.status_code == 200
    assert "Existing connections" in response.text


def test_connections_page_renders_connection_rows(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))
    monkeypatch.delenv("AUTHSOME_DEPLOYMENT_MODE", raising=False)

    with TestClient(create_app()) as client:
        _register_identity(client, tmp_path, "steady-wisely-boldly-0042")
        _seed_connection(
            client,
            identity="steady-wisely-boldly-0042",
            provider="github",
            auth_type=AuthType.OAUTH2,
            access_token="gh-access-token",
            refresh_token="gh-refresh-token",
        )
        response = client.get("/ui/connections")

    assert response.status_code == 200
    assert "Add new connection" in response.text
    assert "connection-row" in response.text


def test_provider_login_modal_copy_is_rendered_when_default_exists(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))
    monkeypatch.delenv("AUTHSOME_DEPLOYMENT_MODE", raising=False)

    with TestClient(create_app()) as client:
        _register_identity(client, tmp_path, "steady-wisely-boldly-0042")
        _seed_connection(
            client,
            identity="steady-wisely-boldly-0042",
            provider="github",
            auth_type=AuthType.OAUTH2,
            access_token="gh-access-token",
            refresh_token="gh-refresh-token",
        )
        response = client.get("/ui/applications")

    assert response.status_code == 200
    assert "Connection name" in response.text
