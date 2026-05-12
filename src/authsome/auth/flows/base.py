"""Abstract base class, result type, and shared flow helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from authlib.integrations.requests_client import OAuth2Session
from loguru import logger

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

    def revoke(
        self,
        provider: ProviderDefinition,
        record: ConnectionRecord,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        """Revoke stored credentials on the remote server (RFC 7009).

        Attempts to revoke the access token first, then the refresh token.
        All exceptions are swallowed and logged as warnings so revocation
        failures cannot block the rest of the logout flow.
        """
        revocation_url = provider.oauth.revocation_url if provider.oauth else None
        if not revocation_url:
            return

        client = OAuth2Session(
            client_id=client_id,
            client_secret=client_secret,
            revocation_endpoint_auth_method="client_secret_post" if client_secret else "none",
        )

        def _do_revoke(token: str, token_type_hint: str) -> None:
            try:
                client.revoke_token(
                    revocation_url,
                    token=token,
                    token_type_hint=token_type_hint,
                    timeout=15,
                )
            except Exception as exc:
                logger.warning(f"{token_type_hint} revocation failed (continuing): {{}}", exc)

        if record.access_token:
            _do_revoke(record.access_token, "access_token")

        if record.refresh_token:
            _do_revoke(record.refresh_token, "refresh_token")


def token_to_connection_record(
    token: dict[str, Any],
    *,
    provider: str,
    profile: str,
    connection_name: str,
    scopes: list[str],
) -> ConnectionRecord:
    """Build a ConnectionRecord from an OAuth2 token response.

    Accepts the dict-shaped token returned by ``OAuth2Session.fetch_token``
    or any equivalent token response with the standard RFC 6749 fields.
    """
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
