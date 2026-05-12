"""Internal HTTP client used by the CLI and local proxy runner."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

import requests

from authsome.server.urls import DEFAULT_SERVER_BASE_URL

DEFAULT_DAEMON_URL = DEFAULT_SERVER_BASE_URL


def resolve_daemon_url(env: Mapping[str, str] | None = None) -> str:
    """Return the configured daemon URL for CLI and proxy clients."""
    values = env if env is not None else os.environ
    raw = values.get("AUTHSOME_DAEMON_URL", DEFAULT_DAEMON_URL).strip()
    return raw.rstrip("/") or DEFAULT_DAEMON_URL


def is_local_daemon_url(url: str) -> bool:
    """Return whether the configured daemon URL targets a local loopback daemon."""
    hostname = urlparse(url).hostname
    return hostname in {"127.0.0.1", "localhost", "::1"}


def is_managed_local_daemon_url(url: str) -> bool:
    """Return whether the URL matches the default local daemon managed by the CLI."""
    parsed = urlparse(url)
    if parsed.scheme != "http":
        return False
    if parsed.path not in {"", "/"}:
        return False
    return parsed.hostname in {"127.0.0.1", "localhost", "::1"} and (parsed.port in {None, 7998})


def raise_for_error(response: requests.Response) -> None:
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        obj = None
        try:
            data = response.json()
            error_name = data.get("error")
            message = data.get("message")
            if error_name and message:
                import authsome.errors as err_mod

                exc_cls = getattr(err_mod, error_name, None)
                if exc_cls and issubclass(exc_cls, err_mod.AuthsomeError):
                    obj = exc_cls.__new__(exc_cls)
                    Exception.__init__(obj, message)
                    obj.provider = data.get("provider")
                    obj.operation = data.get("operation")
        except Exception:
            pass

        if obj is not None:
            raise obj from exc

        raise exc


class AuthsomeApiClient:
    """Small typed wrapper around the daemon API."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = (base_url or resolve_daemon_url()).rstrip("/")

    @property
    def base_url(self) -> str:
        return self._base_url

    async def _get(self, path: str) -> dict[str, Any]:
        response = await asyncio.to_thread(requests.get, f"{self._base_url}{path}", timeout=10)
        raise_for_error(response)
        return response.json()

    async def _post(self, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        response = await asyncio.to_thread(requests.post, f"{self._base_url}{path}", json=body or {}, timeout=30)
        raise_for_error(response)
        return response.json()

    async def _delete(self, path: str) -> dict[str, Any]:
        response = await asyncio.to_thread(requests.delete, f"{self._base_url}{path}", timeout=30)
        raise_for_error(response)
        return response.json()

    async def health(self) -> dict[str, Any]:
        return await self._get("/health")

    async def ready(self) -> dict[str, Any]:
        return await self._get("/ready")

    async def start_login(self, **kwargs: Any) -> dict[str, Any]:
        return await self._post("/auth/sessions", kwargs)

    async def get_session(self, session_id: str) -> dict[str, Any]:
        return await self._get(f"/auth/sessions/{session_id}")

    async def resume_login_session(self, session_id: str, **kwargs: Any) -> dict[str, Any]:
        return await self._post(f"/auth/sessions/{session_id}/resume", {"data": kwargs})

    async def list_connections(self) -> dict[str, Any]:
        return await self._get("/connections")

    async def get_connection(self, provider: str, connection_name: str = "default") -> dict[str, Any]:
        return await self._get(f"/connections/{provider}/{connection_name}")

    async def logout(self, provider: str, connection_name: str = "default") -> None:
        await self._post(f"/connections/{provider}/{connection_name}/logout")

    async def revoke(self, provider: str) -> None:
        await self._post(f"/connections/{provider}/revoke")

    async def set_default_connection(self, provider: str, connection_name: str) -> None:
        await self._post(f"/connections/{provider}/{connection_name}/default")

    async def get_provider(self, provider: str) -> dict[str, Any]:
        return await self._get(f"/providers/{provider}")

    async def register_provider(self, definition_dict: dict[str, Any], force: bool = False) -> None:
        await self._post("/providers", {"definition": definition_dict, "force": force})

    async def remove(self, provider: str) -> None:
        await self._delete(f"/providers/{provider}")

    async def list_providers_by_source(self) -> dict[str, Any]:
        return await self._get("/providers")

    async def export(self, provider: str | None = None, connection_name: str = "default", format: str = "env") -> str:
        result = await self._post(
            "/credentials/export",
            {"provider": provider, "connection": connection_name, "format": format},
        )
        return result["output"]

    async def proxy_routes(self) -> dict[str, Any]:
        return await self._get("/proxy/routes")

    async def resolve_credentials(self, **kwargs: Any) -> dict[str, Any]:
        return await self._post("/credentials/resolve", kwargs)

    async def whoami(self) -> dict[str, Any]:
        return await self._get("/whoami")

    async def doctor(self) -> dict[str, Any]:
        return await self.ready()
