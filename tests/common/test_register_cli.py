"""Tests for the register CLI command."""

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from authsome.cli.main import cli


def test_register_yes_skips_confirmation(tmp_path):
    provider_file = tmp_path / "provider.json"
    provider_file.write_text(
        json.dumps(
            {
                "name": "custom",
                "display_name": "Custom",
                "auth_type": "api_key",
                "flow": "api_key",
                "api_key": {"header_name": "Authorization"},
            }
        ),
        encoding="utf-8",
    )
    client = MagicMock()

    with (
        patch("authsome.cli.main.ensure_daemon", return_value=client),
        patch("authsome.cli.main.audit"),
        patch("authsome.cli.main.click.confirm") as confirm,
    ):
        result = CliRunner().invoke(cli, ["--log-file", "", "register", str(provider_file), "--yes"])

    assert result.exit_code == 0, result.output
    confirm.assert_not_called()
    client.register_provider.assert_called_once()
    assert client.register_provider.call_args.kwargs == {"force": False}
