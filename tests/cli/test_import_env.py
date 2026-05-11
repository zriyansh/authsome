"""Tests for `authsome import-env`."""

from unittest.mock import MagicMock

from click.testing import CliRunner

from authsome.cli.main import cli


def _api_key_provider(name: str, env_var: str) -> dict:
    return {
        "schema_version": 1,
        "name": name,
        "display_name": name.title(),
        "auth_type": "api_key",
        "flow": "api_key",
        "api_key": {"header_name": "Authorization", "header_prefix": "Bearer"},
        "export": {"env": {"api_key": env_var}},
    }


def _oauth_provider(name: str) -> dict:
    return {
        "schema_version": 1,
        "name": name,
        "display_name": name.title(),
        "auth_type": "oauth2",
        "flow": "pkce",
        "oauth": {"authorization_url": "https://example.com/auth", "token_url": "https://example.com/token"},
    }


class TestImportEnvCommand:
    """Behavior tests for headless API key imports."""

    def test_imports_env_key_for_api_provider(self, runner: CliRunner, mock_client: MagicMock, monkeypatch) -> None:
        mock_client.list_connections.return_value = {
            "connections": [],
            "by_source": {
                "bundled": [_api_key_provider("openai", "OPENAI_API_KEY"), _oauth_provider("github")],
                "custom": [],
            },
        }
        mock_client.get_connection.side_effect = Exception("not found")
        mock_client.start_login.return_value = {"id": "sess-1", "status": "pending"}
        mock_client.resume_login_session.return_value = {"id": "sess-1", "status": "completed"}
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-value")

        result = runner.invoke(cli, ["--log-file", "", "import-env"])

        assert result.exit_code == 0, result.output
        mock_client.start_login.assert_called_once_with(
            provider="openai", connection="default", flow="api_key", force=True
        )
        mock_client.resume_login_session.assert_called_once_with("sess-1", api_key="sk-test-value")

    def test_dry_run_does_not_write_credentials(self, runner: CliRunner, mock_client: MagicMock, monkeypatch) -> None:
        mock_client.list_connections.return_value = {
            "connections": [],
            "by_source": {"bundled": [_api_key_provider("openai", "OPENAI_API_KEY")], "custom": []},
        }
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-value")

        result = runner.invoke(cli, ["--log-file", "", "import-env", "--dry-run"])

        assert result.exit_code == 0, result.output
        mock_client.start_login.assert_not_called()
        mock_client.resume_login_session.assert_not_called()
        assert "would_import" in result.output

    def test_skips_unchanged_key_without_force(self, runner: CliRunner, mock_client: MagicMock, monkeypatch) -> None:
        mock_client.list_connections.return_value = {
            "connections": [],
            "by_source": {"bundled": [_api_key_provider("openai", "OPENAI_API_KEY")], "custom": []},
        }
        mock_client.get_connection.return_value = {"status": "connected", "api_key": "sk-same"}
        monkeypatch.setenv("OPENAI_API_KEY", "sk-same")

        result = runner.invoke(cli, ["--log-file", "", "import-env"])

        assert result.exit_code == 0, result.output
        mock_client.start_login.assert_not_called()
        assert "skipped_unchanged" in result.output

    def test_force_reimports_even_when_unchanged(self, runner: CliRunner, mock_client: MagicMock, monkeypatch) -> None:
        mock_client.list_connections.return_value = {
            "connections": [],
            "by_source": {"bundled": [_api_key_provider("openai", "OPENAI_API_KEY")], "custom": []},
        }
        mock_client.get_connection.return_value = {"status": "connected", "api_key": "sk-same"}
        mock_client.start_login.return_value = {"id": "sess-2", "status": "pending"}
        mock_client.resume_login_session.return_value = {"id": "sess-2", "status": "completed"}
        monkeypatch.setenv("OPENAI_API_KEY", "sk-same")

        result = runner.invoke(cli, ["--log-file", "", "import-env", "--force"])

        assert result.exit_code == 0, result.output
        mock_client.start_login.assert_called_once()
        mock_client.resume_login_session.assert_called_once_with("sess-2", api_key="sk-same")
