"""Helpers for resolving the daemon's external URLs."""

from __future__ import annotations

import os
from collections.abc import Mapping

DEFAULT_SERVER_BASE_URL = "http://127.0.0.1:7998"
DEFAULT_CALLBACK_PATH = "/auth/callback/oauth"


def build_server_base_url(env: Mapping[str, str] | None = None) -> str:
    """Return the canonical external base URL for the daemon."""
    values = env if env is not None else os.environ
    raw = values.get("AUTHSOME_SERVER_BASE_URL", DEFAULT_SERVER_BASE_URL).strip()
    return raw.rstrip("/") or DEFAULT_SERVER_BASE_URL


def build_callback_url(base_url: str) -> str:
    """Return the OAuth callback URL for the daemon."""
    return f"{base_url.rstrip('/')}{DEFAULT_CALLBACK_PATH}"


def build_auth_input_url(base_url: str, session_id: str) -> str:
    """Return the browser input page URL for a session."""
    return f"{base_url.rstrip('/')}/auth/sessions/{session_id}/input"


def build_device_url(base_url: str, session_id: str) -> str:
    """Return the browser device-code page URL for a session."""
    return f"{base_url.rstrip('/')}/auth/sessions/{session_id}/device"
