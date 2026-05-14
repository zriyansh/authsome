"""Tests for `authsome login`.

Covers: session started path, session already completed, --force flag,
JSON output shape, and that audit.log is called.
"""

import json
from unittest.mock import MagicMock

from click.testing import CliRunner

from authsome.cli.main import cli


def _started_session(session_id: str = "sess-123") -> dict:
    """Session response where OAuth flow still needs browser interaction."""
    return {
        "id": session_id,
        "status": "pending",
        "next_action": {
            "type": "open_url",
            "url": "https://auth.example.com/oauth?state=xyz",
        },
    }


def _completed_session(session_id: str = "sess-456") -> dict:
    """Session response where login completed immediately (e.g. already connected)."""
    return {
        "id": session_id,
        "status": "completed",
        "next_action": {"type": "none"},
    }


class TestLoginCommand:
    """Tests for `authsome login <provider>`."""

    def test_started_flow_exits_0(self, runner: CliRunner, mock_client: MagicMock) -> None:
        mock_client.start_login.return_value = _started_session()
        result = runner.invoke(cli, ["--log-file", "", "login", "github"])
        assert result.exit_code == 0, result.output

    def test_started_flow_json_output(self, runner: CliRunner, mock_client: MagicMock) -> None:
        mock_client.start_login.return_value = _started_session()
        result = runner.invoke(cli, ["--log-file", "", "login", "github", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["provider"] == "github"
        assert data["status"] == "started"

    def test_completed_flow_json_output(self, runner: CliRunner, mock_client: MagicMock) -> None:
        mock_client.start_login.return_value = _completed_session()
        result = runner.invoke(cli, ["--log-file", "", "login", "openai", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["provider"] == "openai"
        assert data["status"] == "success"

    def test_force_flag_prints_warning(self, runner: CliRunner, mock_client: MagicMock) -> None:
        mock_client.start_login.return_value = _started_session()
        result = runner.invoke(cli, ["--log-file", "", "login", "github", "--force"])
        assert result.exit_code == 0
        assert "Warning" in result.output or "overwrite" in result.output.lower()

    def test_force_flag_quiet_suppresses_warning(self, runner: CliRunner, mock_client: MagicMock) -> None:
        mock_client.start_login.return_value = _started_session()
        result = runner.invoke(cli, ["--log-file", "", "login", "github", "--force", "--quiet"])
        assert result.exit_code == 0
        assert result.output.strip() == ""

    def test_start_login_called_with_provider(self, runner: CliRunner, mock_client: MagicMock) -> None:
        mock_client.start_login.return_value = _started_session()
        runner.invoke(cli, ["--log-file", "", "login", "github"])
        mock_client.start_login.assert_called_once()
        kwargs = mock_client.start_login.call_args.kwargs
        assert kwargs["provider"] == "github"

    def test_started_flow_submits_audit_event(self, runner: CliRunner, mock_client: MagicMock) -> None:
        mock_client.start_login.return_value = _started_session()
        result = runner.invoke(cli, ["--log-file", "", "login", "github"])
        assert result.exit_code == 0, result.output
        mock_client.submit_audit_event.assert_called_once_with(
            event="login",
            provider="github",
            connection="default",
            flow="unknown",
            status="started",
        )

    def test_connection_option_passed_through(self, runner: CliRunner, mock_client: MagicMock) -> None:
        mock_client.start_login.return_value = _started_session()
        runner.invoke(cli, ["--log-file", "", "login", "github", "--connection", "work"])
        kwargs = mock_client.start_login.call_args.kwargs
        assert kwargs["connection"] == "work"

    def test_scopes_option_parsed_as_list(self, runner: CliRunner, mock_client: MagicMock) -> None:
        mock_client.start_login.return_value = _started_session()
        runner.invoke(cli, ["--log-file", "", "login", "github", "--scopes", "repo,read:user"])
        kwargs = mock_client.start_login.call_args.kwargs
        assert kwargs["scopes"] == ["repo", "read:user"]

    def test_login_failure_exits_4(self, runner: CliRunner, mock_client: MagicMock) -> None:
        from authsome.errors import ProviderNotFoundError

        mock_client.start_login.side_effect = ProviderNotFoundError("nope")
        result = runner.invoke(cli, ["--log-file", "", "login", "nope"])
        assert result.exit_code == 4
