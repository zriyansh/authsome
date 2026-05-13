"""Tests for `authsome init`."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock

from click.testing import CliRunner

from authsome.cli.main import cli
from authsome.store.local import LocalAppStore


def test_init_removes_legacy_default_state_and_registers_identity(
    runner: CliRunner,
    mock_client: MagicMock,
    tmp_path: Path,
) -> None:
    identities = tmp_path / "identities"
    identities.mkdir(parents=True)
    (identities / "default.json").write_text("{}", encoding="utf-8")
    (identities / "default.key").write_text("legacy\n", encoding="utf-8")

    asyncio.run(LocalAppStore(tmp_path).ensure_initialized())

    result = runner.invoke(cli, ["--log-file", "", "init", "--json"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["identity"] != "default"
    assert data["registration_status"] == "registered"
    assert not (identities / "default.json").exists()
    assert not (identities / "default.key").exists()
    mock_client.register_identity.assert_called_once_with(data["identity"], data["did"])

    async def read_config_after_init() -> dict:
        store = LocalAppStore(tmp_path)
        config = await store.get_config()
        return config.model_dump()

    config_data = asyncio.run(read_config_after_init())
    assert config_data["active_identity"] == data["identity"]
