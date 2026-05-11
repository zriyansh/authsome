"""Abstract base class, result type, and shared OAuth helpers for authentication flows."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from authlib.integrations.requests_client import OAuth2Session

from authsome.auth.models.connection import AccountInfo, ConnectionRecord, ProviderClientRecord
from authsome.auth.models.enums import AuthType, ConnectionStatus
from authsome.auth.models.provider import ProviderDefinition
from authsome.server.urls import DEFAULT_SERVER_BASE_URL, build_callback_url
from authsome.utils import utc_now

if TYPE_CHECKING:
    from authsome.auth.sessions import AuthSession


DEFAULT_CALLBACK_URL = build_callback_url(DEFAULT_SERVER_BASE_URL)


@dataclass
class FlowResult:
    """Returned by every flow's authenticate() method.

    client_record is only populated by DCR-based flows that register a new
    OAuth client as part of the authentication process.
    """

    connection: ConnectionRecord
    client_record: ProviderClientRecord | None = None


class AuthFlow(ABC):
    """Abstract authentication flow handler.

    Flows return FlowResult with plaintext credential fields.
    Encryption is handled by the Vault when the record is persisted.
    """

    @abstractmethod
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
        """Start the authentication flow.

        Must populate runtime_session.payload with flow-specific data
        and transition the session to 'waiting_for_user' or 'processing'.
        """
        ...

    @abstractmethod
    def resume(
        self,
        provider: ProviderDefinition,
        profile: str,
        connection_name: str,
        runtime_session: AuthSession,
        callback_data: dict[str, Any],
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> FlowResult | None:
        """Resume the authentication flow with callback or input data.

        Returns the final FlowResult or None if the flow is still pending.
        """
        ...

def build_oauth_session(**kwargs: Any) -> OAuth2Session:
    """OAuth2Session pinned to ``client_secret_post`` when a secret is present.

    authlib defaults to HTTP Basic; authsome has always sent credentials in
    the body, and DCR clients are registered with ``client_secret_post``.
    """
    auth_method = "client_secret_post" if kwargs.get("client_secret") else "none"
    return OAuth2Session(token_endpoint_auth_method=auth_method, **kwargs)


def token_to_connection_record(
    token: dict[str, Any],
    *,
    provider: str,
    profile: str,
    connection_name: str,
    scopes: list[str],
) -> ConnectionRecord:
    """Build a ConnectionRecord from an authlib OAuth2Token dict."""
    now = utc_now()
    expires_in = token.get("expires_in")
    return ConnectionRecord(
        schema_version=2,
        provider=provider,
        profile=profile,
        connection_name=connection_name,
        auth_type=AuthType.OAUTH2,
        status=ConnectionStatus.CONNECTED,
        scopes=scopes,
        access_token=token.get("access_token", ""),
        refresh_token=token.get("refresh_token"),
        token_type=token.get("token_type", "Bearer"),
        expires_at=now + timedelta(seconds=int(expires_in)) if expires_in else None,
        obtained_at=now,
        account=AccountInfo(),
    )
