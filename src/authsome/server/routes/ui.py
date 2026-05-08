"""HTML routes that render the Authsome local dashboard.

The UI is intentionally server-rendered against the same FastAPI app that
serves the JSON daemon API. This keeps it a single process on port 7998
and avoids a separate static server.
"""

from __future__ import annotations

from datetime import UTC, datetime
from importlib.resources import files
from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from authsome import __version__
from authsome.auth import AuthService
from authsome.auth.models.enums import AuthType
from authsome.auth.models.provider import ProviderDefinition
from authsome.errors import ConnectionNotFoundError
from authsome.server.routes._deps import get_auth_service

router = APIRouter(prefix="/ui", tags=["ui"], include_in_schema=False)

# Templates ship inside the installed package alongside the code.
_TEMPLATES_DIR = files("authsome.ui").joinpath("templates")
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _format_relative(when: datetime | None) -> str | None:
    """Return a compact "in 47 minutes" / "2 days ago" label."""
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    delta_seconds = int((when - datetime.now(UTC)).total_seconds())
    abs_seconds = abs(delta_seconds)
    direction = "in" if delta_seconds >= 0 else "ago"

    if abs_seconds < 60:
        amount, unit = abs_seconds, "second"
    elif abs_seconds < 3600:
        amount, unit = abs_seconds // 60, "minute"
    elif abs_seconds < 86400:
        amount, unit = abs_seconds // 3600, "hour"
    else:
        amount, unit = abs_seconds // 86400, "day"

    plural = "" if amount == 1 else "s"
    return f"{direction} {amount} {unit}{plural}" if direction == "in" else f"{amount} {unit}{plural} ago"


def _provider_status(provider_name: str, connection_summaries: list[dict[str, Any]]) -> str:
    """Map a connection list to a single status string for the overview cards."""
    if not connection_summaries:
        return "available"
    statuses = {c.get("status") for c in connection_summaries}
    if "error" in statuses or "expired" in statuses:
        return "reauth"
    return "connected"


def _logo_initial(name: str) -> str:
    return (name[:1] or "?").upper()


def _build_provider_view(
    provider: ProviderDefinition,
    source: str,
    connections: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "name": provider.name,
        "display_name": provider.display_name,
        "auth_type": provider.auth_type.value,
        "auth_type_label": "OAuth 2.0" if provider.auth_type == AuthType.OAUTH2 else "API Key",
        "host_url": provider.host_url or (provider.oauth.base_url if provider.oauth else None) or provider.name,
        "description": (provider.metadata or {}).get("description", ""),
        "source": source,
        "logo_initial": _logo_initial(provider.display_name or provider.name),
        "status": _provider_status(provider.name, connections),
        "connections": connections,
        "scope_count": len(connections[0].get("scopes") or []) if connections else 0,
    }


def _all_provider_views(auth: AuthService) -> list[dict[str, Any]]:
    by_source = auth.list_providers_by_source()
    connections_by_provider = {group["name"]: group["connections"] for group in auth.list_connections()}
    views: list[dict[str, Any]] = []
    for source in ("bundled", "custom"):
        for provider in by_source.get(source, []):
            views.append(_build_provider_view(provider, source, connections_by_provider.get(provider.name, [])))
    return views


@router.get("/", response_class=HTMLResponse)
def overview(request: Request, auth: AuthService = Depends(get_auth_service)) -> HTMLResponse:
    providers = _all_provider_views(auth)
    connected = [p for p in providers if p["status"] != "available"]
    available_count = len(providers) - len(connected)
    oauth_count = sum(1 for p in connected if p["auth_type"] == AuthType.OAUTH2.value)
    apikey_count = sum(1 for p in connected if p["auth_type"] == AuthType.API_KEY.value)

    # "Last activity" ~ most recent token issue/refresh time across connections.
    last_activity_label: str | None = None
    most_recent: datetime | None = None
    for view in connected:
        for conn in view["connections"]:
            for ts_field in ("expires_at",):
                ts = conn.get(ts_field)
                if not ts:
                    continue
                try:
                    parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except (TypeError, ValueError):
                    continue
                if most_recent is None or parsed > most_recent:
                    most_recent = parsed
    if most_recent is not None:
        last_activity_label = _format_relative(most_recent)

    return templates.TemplateResponse(
        request,
        "overview.html",
        {
            "page": "overview",
            "version": __version__,
            "stats": {
                "connected": len(connected),
                "available": available_count,
                "oauth": oauth_count,
                "api_key": apikey_count,
            },
            "last_activity": last_activity_label or "—",
            "connected_providers": connected[:6],
        },
    )


@router.get("/connections", response_class=HTMLResponse)
def connections(request: Request, auth: AuthService = Depends(get_auth_service)) -> HTMLResponse:
    providers = _all_provider_views(auth)
    connected_count = sum(1 for p in providers if p["status"] != "available")
    return templates.TemplateResponse(
        request,
        "connections.html",
        {
            "page": "connections",
            "version": __version__,
            "providers": providers,
            "totals": {
                "all": len(providers),
                "connected": connected_count,
                "available": len(providers) - connected_count,
            },
        },
    )


@router.get("/apps/{provider_name}", response_class=HTMLResponse)
def app_detail(
    provider_name: str,
    request: Request,
    auth: AuthService = Depends(get_auth_service),
) -> Response:
    provider = auth.get_provider(provider_name)

    connection_record = None
    try:
        connection_record = auth.get_connection(provider_name)
    except ConnectionNotFoundError:
        pass

    # Disconnected detail pages are explicitly out of scope in the mockup.
    if connection_record is None:
        return RedirectResponse(url=f"/ui/connections#{provider_name}", status_code=303)

    client_record = auth.get_provider_client(provider_name)
    redirect_uri = "http://127.0.0.1:7998/auth/callback/oauth"

    common = {
        "page": "connections",
        "version": __version__,
        "provider": provider,
        "connection": connection_record,
        "logo_initial": _logo_initial(provider.display_name or provider.name),
        "host_url": provider.host_url or (provider.oauth.base_url if provider.oauth else None) or provider.name,
        "expires_label": _format_relative(connection_record.expires_at),
        "obtained_label": _format_relative(connection_record.obtained_at),
        "scopes": connection_record.scopes or [],
    }

    if provider.auth_type == AuthType.OAUTH2:
        return templates.TemplateResponse(
            request,
            "app_detail_oauth.html",
            {
                **common,
                "client_id": (client_record.client_id if client_record else None),
                "has_client_secret": bool(client_record and client_record.client_secret),
                "redirect_uri": redirect_uri,
                "auth_url": provider.oauth.authorization_url if provider.oauth else "",
                "token_url": provider.oauth.token_url if provider.oauth else "",
                "access_token": connection_record.access_token,
                "refresh_token": connection_record.refresh_token,
            },
        )

    return templates.TemplateResponse(
        request,
        "app_detail_apikey.html",
        {
            **common,
            "api_key": connection_record.api_key,
            "base_url": connection_record.base_url
            or (provider.oauth.base_url if provider.oauth else None)
            or provider.host_url,
        },
    )


@router.post("/apps/{provider_name}/{connection_name}/disconnect")
def disconnect_app(
    provider_name: str,
    connection_name: str,
    auth: AuthService = Depends(get_auth_service),
) -> RedirectResponse:
    """Disconnect a provider connection from the dashboard."""
    auth.logout(provider_name, connection_name)
    return RedirectResponse(url="/ui/connections", status_code=303)
