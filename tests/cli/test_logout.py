"""Tests for `authsome logout`.

Covers: successful logout, JSON output, and that the daemon
client's logout method is called with the right arguments.
"""

import json
from unittest.mock import MagicMock

from click.testing import CliRunner

from authsome.cli.main import cli


class TestLogoutCommand:
    """Tests for `authsome logout <provider>`."""

    def test_logout_exits_0(self, runner: CliRunner, mock_client: MagicMock) -> None:
        result = runner.invoke(cli, ["--log-file", "", "logout", "github"])
        assert result.exit_code == 0, result.output

    def test_logout_human_output(self, runner: CliRunner, mock_client: MagicMock) -> None:
        result = runner.invoke(cli, ["--log-file", "", "logout", "github"])
        assert "Logged out" in result.output
        assert "github" in result.output

    def test_logout_json_output(self, runner: CliRunner, mock_client: MagicMock) -> None:
        result = runner.invoke(cli, ["--log-file", "", "logout", "github", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "logged_out"
        assert data["provider"] == "github"
        assert data["connection"] == "default"

    def test_logout_connection_option(self, runner: CliRunner, mock_client: MagicMock) -> None:
        result = runner.invoke(cli, ["--log-file", "", "logout", "github", "--connection", "work"])
        assert result.exit_code == 0
        mock_client.logout.assert_called_once_with("github", "work")

    def test_logout_calls_client(self, runner: CliRunner, mock_client: MagicMock) -> None:
        runner.invoke(cli, ["--log-file", "", "logout", "openai"])
        mock_client.logout.assert_called_once_with("openai", "default")

    def test_logout_provider_not_found_exits_4(self, runner: CliRunner, mock_client: MagicMock) -> None:
        from authsome.errors import ProviderNotFoundError

        mock_client.logout.side_effect = ProviderNotFoundError("nope")
        result = runner.invoke(cli, ["--log-file", "", "logout", "nope"])
        assert result.exit_code == 4
