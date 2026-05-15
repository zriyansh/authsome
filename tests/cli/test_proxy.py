"""Tests for ``authsome proxy mode``."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from click.testing import CliRunner

from authsome.cli.main import cli
from authsome.server.dependencies import load_server_config
from authsome.store.local import LocalAppStore


def test_proxy_mode_defaults_to_connected_allow_when_unset(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    asyncio.run(LocalAppStore(tmp_path).ensure_initialized())

    result = runner.invoke(cli, ["--log-file", "", "proxy", "mode", "--json"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["mode"] == "connected_allow"


def test_proxy_mode_sets_and_persists_value(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    asyncio.run(LocalAppStore(tmp_path).ensure_initialized())

    set_result = runner.invoke(cli, ["--log-file", "", "proxy", "mode", "configured_deny", "--json"])
    assert set_result.exit_code == 0, set_result.output
    set_data = json.loads(set_result.output)
    assert set_data["status"] == "updated"
    assert set_data["mode"] == "configured_deny"

    persisted = load_server_config(tmp_path)
    assert persisted.proxy is not None
    assert persisted.proxy.mode == "configured_deny"

    show_result = runner.invoke(cli, ["--log-file", "", "proxy", "mode", "--json"])
    assert show_result.exit_code == 0, show_result.output
    assert json.loads(show_result.output)["mode"] == "configured_deny"


def test_proxy_mode_rejects_unknown_value(runner: CliRunner, tmp_path: Path) -> None:
    asyncio.run(LocalAppStore(tmp_path).ensure_initialized())

    result = runner.invoke(cli, ["--log-file", "", "proxy", "mode", "bogus"])
    assert result.exit_code != 0
    assert "Invalid value" in result.output or "invalid choice" in result.output.lower()
