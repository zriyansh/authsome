"""Tests for `authsome identity` commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from click.testing import CliRunner

from authsome.cli.main import cli
from authsome.identity.keys import load_identity


class TestIdentityCommands:
    """Tests for local identity management commands."""

    def test_identity_create_writes_local_keypair(
        self, runner: CliRunner, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        result = runner.invoke(
            cli,
            ["--log-file", "", "identity", "create", "--handle", "steady-wisely-boldly-0042", "--json"],
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["status"] == "created"
        assert data["identity"] == "steady-wisely-boldly-0042"
        stored = load_identity(tmp_path, "steady-wisely-boldly-0042")
        assert stored.did == data["did"]

    def test_identity_register_uses_existing_local_identity(
        self, runner: CliRunner, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        runner.invoke(cli, ["--log-file", "", "identity", "create", "--handle", "steady-wisely-boldly-0042"])
        stored = load_identity(tmp_path, "steady-wisely-boldly-0042")
        mock_client.register_identity.return_value = {
            "status": "registered",
            "identity": stored.handle,
            "did": stored.did,
        }

        result = runner.invoke(
            cli,
            ["--log-file", "", "identity", "register", "steady-wisely-boldly-0042", "--json"],
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["status"] == "registered"
        assert data["identity"] == stored.handle
        assert data["did"] == stored.did
        mock_client.register_identity.assert_called_once_with(stored.handle, stored.did)
