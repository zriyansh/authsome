import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from authsome.cli.client import AuthsomeApiClient


@pytest.mark.asyncio
async def test_protected_request_sends_pop_header(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))
    captured: dict = {}

    def fake_request(method, url, data=None, headers=None, timeout=None):
        captured.update({"method": method, "url": url, "data": data, "headers": headers, "timeout": timeout})
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"connections": [], "by_source": {"bundled": [], "custom": []}}
        return response

    monkeypatch.setattr("authsome.cli.client.requests.request", fake_request)

    await AuthsomeApiClient("http://127.0.0.1:7998").list_connections()

    assert captured["headers"]["Authorization"].startswith("PoP ")


@pytest.mark.asyncio
async def test_health_request_is_unsigned(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))
    captured: dict = {}

    def fake_request(method, url, data=None, headers=None, timeout=None):
        captured.update({"method": method, "url": url, "data": data, "headers": headers, "timeout": timeout})
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"status": "ok", "version": "0.0.0"}
        return response

    monkeypatch.setattr("authsome.cli.client.requests.request", fake_request)

    await AuthsomeApiClient("http://127.0.0.1:7998").health()

    assert "Authorization" not in captured["headers"]


@pytest.mark.asyncio
async def test_post_body_is_signed_as_sent(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTHSOME_HOME", str(tmp_path))
    captured: dict = {}

    def fake_request(method, url, data=None, headers=None, timeout=None):
        captured.update({"method": method, "url": url, "data": data, "headers": headers, "timeout": timeout})
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"status": "ok"}
        return response

    monkeypatch.setattr("authsome.cli.client.requests.request", fake_request)

    await AuthsomeApiClient("http://127.0.0.1:7998").set_default_connection("github", "work")

    assert captured["data"] == json.dumps({}, separators=(",", ":"), sort_keys=True).encode("utf-8")
