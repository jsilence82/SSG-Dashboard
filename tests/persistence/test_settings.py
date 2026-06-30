import json
from unittest.mock import MagicMock, call, patch

import pytest

import ssg_dashboard.persistence.settings as mod


@pytest.fixture
def settings_file(tmp_path, monkeypatch):
    path = tmp_path / "ssg_settings.json"
    monkeypatch.setattr(mod, "SETTINGS_FILE", path)
    return path


@pytest.fixture
def mock_keyring(monkeypatch):
    kr = MagicMock()
    kr.get_password.return_value = None
    monkeypatch.setattr(mod, "keyring", kr)
    return kr


@pytest.fixture(autouse=True)
def force_dev_mode(monkeypatch):
    """These tests assert on keyring fallback behavior, which only runs in dev
    mode and only when st.secrets has no entry for the credential. Both
    _is_production() and get_credential() read st.secrets directly, so a
    developer's local .streamlit/secrets.toml leaks real credentials into
    these tests unless st.secrets is neutralized too."""
    monkeypatch.setattr(mod, "_is_production", lambda: False)
    monkeypatch.setattr(mod.st, "secrets", {})


class TestApiKey:
    def test_save_api_key_calls_keyring(self, settings_file, mock_keyring):
        mod.save_api_key("mykey123")
        mock_keyring.set_password.assert_called_once_with("ssg_dashboard", "tt_api_key", "mykey123")

    def test_save_api_key_strips_whitespace(self, settings_file, mock_keyring):
        mod.save_api_key("  mykey  ")
        mock_keyring.set_password.assert_called_once_with("ssg_dashboard", "tt_api_key", "mykey")

    def test_load_api_key_reads_from_keyring(self, settings_file, mock_keyring):
        mock_keyring.get_password.return_value = "storedkey"
        assert mod.load_api_key() == "storedkey"
        mock_keyring.get_password.assert_called_with("ssg_dashboard", "tt_api_key")

    def test_load_api_key_migrates_from_json_when_keyring_empty(self, settings_file, mock_keyring):
        settings_file.write_text(json.dumps({"api_key": "oldkey"}), encoding="utf-8")
        mock_keyring.get_password.return_value = None

        result = mod.load_api_key()

        assert result == "oldkey"
        mock_keyring.set_password.assert_called_once_with("ssg_dashboard", "tt_api_key", "oldkey")

    def test_migration_removes_key_from_json(self, settings_file, mock_keyring):
        settings_file.write_text(json.dumps({"api_key": "oldkey", "other": "keep"}), encoding="utf-8")
        mock_keyring.get_password.return_value = None

        mod.load_api_key()

        remaining = json.loads(settings_file.read_text())
        assert "api_key" not in remaining
        assert remaining.get("other") == "keep"


class TestPaypalSettings:
    def test_save_writes_secrets_to_keyring(self, settings_file, mock_keyring):
        mod.save_paypal_settings("cid123", "sec456", False)
        mock_keyring.set_password.assert_any_call("ssg_dashboard", "pp_client_id", "cid123")
        mock_keyring.set_password.assert_any_call("ssg_dashboard", "pp_client_secret", "sec456")

    def test_save_writes_sandbox_flag_to_json(self, settings_file, mock_keyring):
        mod.save_paypal_settings("cid", "sec", True)
        data = json.loads(settings_file.read_text())
        assert data["pp_sandbox"] is True

    def test_load_reads_secrets_from_keyring(self, settings_file, mock_keyring):
        settings_file.write_text(json.dumps({"pp_sandbox": True}), encoding="utf-8")
        mock_keyring.get_password.side_effect = lambda svc, key: {
            "pp_client_id": "cid_from_kr",
            "pp_client_secret": "sec_from_kr",
        }.get(key)

        cid, secret, sandbox = mod.load_paypal_settings()
        assert cid == "cid_from_kr"
        assert secret == "sec_from_kr"
        assert sandbox is True

    def test_load_migrates_from_json_when_keyring_empty(self, settings_file, mock_keyring):
        settings_file.write_text(
            json.dumps({"pp_client_id": "oldcid", "pp_secret": "oldsec", "pp_sandbox": False}),
            encoding="utf-8",
        )
        mock_keyring.get_password.return_value = None

        cid, secret, _ = mod.load_paypal_settings()
        assert cid == "oldcid"
        assert secret == "oldsec"

        remaining = json.loads(settings_file.read_text())
        assert "pp_client_id" not in remaining
        assert "pp_secret" not in remaining


class TestWriteSettings:
    def test_never_writes_secrets_to_json(self, settings_file, mock_keyring):
        mod._write_settings({"api_key": "k", "pp_client_id": "c", "pp_secret": "s", "mapping": {}})
        data = json.loads(settings_file.read_text())
        assert "api_key" not in data
        assert "pp_client_id" not in data
        assert "pp_secret" not in data

    def test_non_secret_fields_persisted(self, settings_file, mock_keyring):
        mod._write_settings({"pp_sandbox": True, "mapping": {"show": "col"}})
        data = json.loads(settings_file.read_text())
        assert data["pp_sandbox"] is True
        assert data["mapping"] == {"show": "col"}

    def test_merges_with_existing_settings(self, settings_file, mock_keyring):
        settings_file.write_text(json.dumps({"existing": "value"}), encoding="utf-8")
        mod._write_settings({"new": "field"})
        data = json.loads(settings_file.read_text())
        assert data["existing"] == "value"
        assert data["new"] == "field"
