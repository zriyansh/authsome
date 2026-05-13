from pathlib import Path
from unittest.mock import Mock, patch

from authsome.store.local import _ensure_macos_keychain_ca


class TestEnsureMacosKeychainCa:
    """Tests for the centralized macOS CA keychain trust installer."""

    def test_skips_on_non_macos(self) -> None:
        with patch("authsome.store.local.sys") as mock_sys, patch("authsome.store.local.subprocess.run") as run_mock:
            mock_sys.platform = "linux"
            _ensure_macos_keychain_ca()

        run_mock.assert_not_called()

    def _make_fake_keychain(self, tmp_path: Path) -> Path:
        """Create a fake login.keychain-db under the tmp_path home structure."""
        keychain_dir = tmp_path / "Library" / "Keychains"
        keychain_dir.mkdir(parents=True)
        keychain = keychain_dir / "login.keychain-db"
        keychain.touch()
        return keychain

    def test_skips_when_already_present(self, tmp_path: Path) -> None:
        self._make_fake_keychain(tmp_path)

        with (
            patch("authsome.store.local.sys") as mock_sys,
            patch("authsome.store.local.Path.home", return_value=tmp_path),
            patch("authsome.store.local.subprocess.run") as run_mock,
        ):
            mock_sys.platform = "darwin"
            # find-certificate returns 0 → cert already present
            run_mock.return_value = Mock(returncode=0)
            _ensure_macos_keychain_ca()

        # Only the find-certificate check should have run
        assert run_mock.call_count == 1
        assert "find-certificate" in run_mock.call_args[0][0]

    def test_generates_cert_and_adds_to_keychain(self, tmp_path: Path) -> None:
        self._make_fake_keychain(tmp_path)
        mitm_dir = tmp_path / ".mitmproxy"
        mitm_dir.mkdir()
        ca_cert = mitm_dir / "mitmproxy-ca-cert.pem"

        def mock_from_store(path, basename, key_size):
            # Simulate CertStore generating the file
            ca_cert.write_text("fake-cert-data")

        find_result = Mock(returncode=1)  # cert not present
        add_result = Mock(returncode=0)  # add succeeded

        with (
            patch("authsome.store.local.sys") as mock_sys,
            patch("authsome.store.local.Path.home", return_value=tmp_path),
            patch("authsome.store.local.subprocess.run", side_effect=[find_result, add_result]) as run_mock,
            patch("mitmproxy.certs.CertStore.from_store", side_effect=mock_from_store) as gen_mock,
        ):
            mock_sys.platform = "darwin"
            _ensure_macos_keychain_ca()

        # Should have attempted generation and added to keychain
        gen_mock.assert_called_once()
        assert ca_cert.exists()
        assert run_mock.call_count == 2
        assert "add-trusted-cert" in run_mock.call_args_list[1][0][0]

    def test_aborts_if_generation_fails(self, tmp_path: Path) -> None:
        self._make_fake_keychain(tmp_path)
        mitm_dir = tmp_path / ".mitmproxy"
        mitm_dir.mkdir()

        find_result = Mock(returncode=1)  # cert not present

        with (
            patch("authsome.store.local.sys") as mock_sys,
            patch("authsome.store.local.Path.home", return_value=tmp_path),
            patch("authsome.store.local.subprocess.run", return_value=find_result) as run_mock,
            patch("mitmproxy.certs.CertStore.from_store", side_effect=RuntimeError("boom")) as gen_mock,
        ):
            mock_sys.platform = "darwin"
            _ensure_macos_keychain_ca()

        # Generation failed, so should NOT have tried to add to keychain
        gen_mock.assert_called_once()
        assert run_mock.call_count == 1  # Only find-certificate was called
