"""DCR + PKCE OAuth2 flow."""

from __future__ import annotations

import json
import urllib.parse
from typing import TYPE_CHECKING, Any

import requests as http_client
from authlib.common.security import generate_token
from authlib.integrations.base_client.errors import OAuthError

from authsome.auth.flows.base import (
    DEFAULT_CALLBACK_URL,
    AuthFlow,
    FlowResult,
    build_oauth_session,
    token_to_connection_record,
)
from authsome.auth.models.connection import ProviderClientRecord
from authsome.auth.models.provider import ProviderDefinition
from authsome.errors import AuthenticationFailedError, DiscoveryError

if TYPE_CHECKING:
    from authsome.auth.sessions import AuthSession


class DcrPkceFlow(AuthFlow):
    """Dynamic Client Registration + PKCE authorization code flow."""

    callback_port: int = 7999

    def begin(
        self,
        provider: ProviderDefinition,
        profile: str,
        connection_name: str,
        runtime_session: AuthSession,
        scopes: list[str] | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        base_url: str | None = None,
    ) -> None:
        if provider.oauth is None:
            raise AuthenticationFailedError("Provider missing 'oauth' configuration", provider=provider.name)

        effective_scopes = scopes or provider.oauth.scopes or []
        redirect_uri = runtime_session.payload.get("callback_url_override") or DEFAULT_CALLBACK_URL

        registered_new_client = not client_id
        if registered_new_client:
            client_id, client_secret = self._register_client(provider, effective_scopes, redirect_uri)

        assert client_id is not None  # either passed in or registered above

        code_verifier = generate_token(48)

        client = build_oauth_session(
            client_id=client_id,
            client_secret=client_secret,
            scope=" ".join(effective_scopes) if effective_scopes else None,
            redirect_uri=redirect_uri,
            code_challenge_method="S256",
        )
        auth_url, state = client.create_authorization_url(
            provider.oauth.authorization_url,
            code_verifier=code_verifier,
        )

        runtime_session.state = "waiting_for_user"
        runtime_session.payload["auth_url"] = auth_url
        runtime_session.payload["callback_url"] = redirect_uri
        runtime_session.payload["internal_code_verifier"] = code_verifier
        runtime_session.payload["internal_state"] = state
        runtime_session.payload["internal_scopes"] = json.dumps(effective_scopes)
        if registered_new_client:
            runtime_session.payload["internal_client_id"] = client_id
            if client_secret:
                runtime_session.payload["internal_client_secret"] = client_secret

    def resume(
        self,
        provider: ProviderDefinition,
        profile: str,
        connection_name: str,
        runtime_session: AuthSession,
        callback_data: dict[str, Any],
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> FlowResult:
        if provider.oauth is None:
            raise AuthenticationFailedError("Provider missing 'oauth' configuration", provider=provider.name)

        error = callback_data.get("error")
        if error:
            raise AuthenticationFailedError(f"OAuth error: {error}", provider=provider.name)

        auth_code = callback_data.get("code")
        if not auth_code:
            raise AuthenticationFailedError("Authorization timed out or no code received", provider=provider.name)

        returned_state = callback_data.get("state")
        expected_state = runtime_session.payload.get("internal_state")
        if returned_state != expected_state:
            raise AuthenticationFailedError("OAuth state mismatch — potential CSRF attack", provider=provider.name)

        # DCR-registered credentials live on the session payload; user-supplied
        # credentials are passed in via kwargs.
        if "internal_client_id" in runtime_session.payload:
            client_id = runtime_session.payload["internal_client_id"]
            client_secret = runtime_session.payload.get("internal_client_secret")
            registered_new_client = True
        else:
            registered_new_client = False

        if not client_id:
            raise AuthenticationFailedError("DCR PKCE flow requires a client_id.", provider=provider.name)

        code_verifier = runtime_session.payload.get("internal_code_verifier", "")
        redirect_uri = runtime_session.payload.get("callback_url", "")
        effective_scopes = json.loads(runtime_session.payload.get("internal_scopes", "[]"))

        client = build_oauth_session(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )
        try:
            token = client.fetch_token(
                provider.oauth.token_url,
                grant_type="authorization_code",
                code=auth_code,
                code_verifier=code_verifier,
            )
        except OAuthError as exc:
            raise AuthenticationFailedError(
                f"Token exchange error: {exc.error} — {exc.description or 'Unknown error'}",
                provider=provider.name,
            ) from exc
        except http_client.RequestException as exc:
            raise AuthenticationFailedError(f"Token exchange failed: {exc}", provider=provider.name) from exc

        runtime_session.state = "processing"

        dcr_client = (
            ProviderClientRecord(
                schema_version=2,
                profile=profile,
                provider=provider.name,
                client_id=client_id,
                client_secret=client_secret,
            )
            if registered_new_client
            else None
        )
        return FlowResult(
            connection=token_to_connection_record(
                dict(token),
                provider=provider.name,
                profile=profile,
                connection_name=connection_name,
                scopes=effective_scopes,
            ),
            client_record=dcr_client,
        )

    def _discover_registration_endpoint(self, provider: ProviderDefinition) -> str:
        if provider.oauth is None:
            raise DiscoveryError("No OAuth config", provider=provider.name)
        parsed = urllib.parse.urlparse(provider.oauth.authorization_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        for url in [
            f"{base_url}/.well-known/openid-configuration",
            f"{base_url}/.well-known/oauth-authorization-server",
        ]:
            try:
                resp = http_client.get(url, timeout=15)
                if resp.status_code == 200:
                    reg_endpoint = resp.json().get("registration_endpoint")
                    if reg_endpoint:
                        return reg_endpoint
            except (http_client.RequestException, json.JSONDecodeError):
                continue
        raise DiscoveryError(
            "Could not discover registration_endpoint via .well-known. "
            "Set oauth.registration_endpoint in the provider definition.",
            provider=provider.name,
        )

    def _register_client(
        self, provider: ProviderDefinition, scopes: list[str], redirect_uri: str
    ) -> tuple[str, str | None]:
        if provider.oauth is None:
            raise AuthenticationFailedError("No OAuth config", provider=provider.name)
        reg_endpoint = provider.oauth.registration_endpoint or self._discover_registration_endpoint(provider)
        dcr_payload: dict[str, Any] = {
            "client_name": f"authsome-{provider.name}",
            "redirect_uris": [redirect_uri],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "client_secret_post",
            "code_challenge_methods_supported": ["S256"],
        }
        if scopes:
            dcr_payload["scope"] = " ".join(scopes)

        try:
            resp = http_client.post(
                reg_endpoint, json=dcr_payload, headers={"Content-Type": "application/json"}, timeout=30
            )
            resp.raise_for_status()
            reg_data = resp.json()
        except http_client.RequestException as exc:
            raise AuthenticationFailedError(
                f"Dynamic Client Registration failed: {exc}", provider=provider.name
            ) from exc
        except json.JSONDecodeError as exc:
            raise AuthenticationFailedError("DCR response was not valid JSON", provider=provider.name) from exc

        client_id = reg_data.get("client_id")
        if not client_id:
            raise AuthenticationFailedError("DCR response missing client_id", provider=provider.name)
        return client_id, reg_data.get("client_secret")
