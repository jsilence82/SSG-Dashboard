"""Persisted user settings — column mappings, capacity overrides, API credentials."""

import json
from datetime import datetime, timezone

import keyring
import keyring.errors

from ..config import SETTINGS_FILE

_SERVICE = "ssg_dashboard"


def _keyring_available() -> bool:
    try:
        keyring.get_password(_SERVICE, "_probe")
        return True
    except (keyring.errors.NoKeyringError, RuntimeError):
        return False


def _kr_get(key: str) -> str:
    try:
        return keyring.get_password(_SERVICE, key) or ""
    except (keyring.errors.NoKeyringError, RuntimeError):
        return ""


def _kr_set(key: str, value: str) -> None:
    """Raises KeyError if no keyring backend is available."""
    try:
        keyring.set_password(_SERVICE, key, value)
    except (keyring.errors.NoKeyringError, RuntimeError) as exc:
        raise KeyError(
            "No secure credential store is available on this system. "
            "On Windows, ensure pywin32-ctypes is installed: "
            "pip install pywin32-ctypes"
        ) from exc


def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        return {}
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_settings(payload: dict) -> None:
    existing = load_settings()
    existing.update(payload)
    for k in ("api_key", "pp_client_id", "pp_secret"):
        existing.pop(k, None)
    existing["saved_at"] = datetime.now(timezone.utc).isoformat()
    SETTINGS_FILE.write_text(json.dumps(existing), encoding="utf-8")


def save_api_key(api_key: str) -> None:
    _kr_set("tt_api_key", api_key.strip())


def load_api_key() -> str:
    key = _kr_get("tt_api_key")
    if key:
        return key
    # One-time migration: move key from old JSON storage into keychain
    old = load_settings().get("api_key", "")
    if old:
        try:
            _kr_set("tt_api_key", old)
            _write_settings({})
        except KeyError:
            pass
    return old


def save_mapping_settings(mapping: dict, prices_in_cents: bool,
                           revenue_is_per_unit: bool, raw_columns: list | None = None) -> None:
    payload = {"mapping": mapping, "prices_in_cents": prices_in_cents,
               "revenue_is_per_unit": revenue_is_per_unit}
    if raw_columns is not None:
        payload["raw_columns"] = list(raw_columns)
    _write_settings(payload)


def save_capacities(capacity: dict) -> None:
    _write_settings({"capacity": {k: v for k, v in capacity.items() if v}})


def load_capacities() -> dict:
    return load_settings().get("capacity", {})


def save_paypal_settings(client_id: str, secret: str, sandbox: bool) -> None:
    _kr_set("pp_client_id", client_id.strip())
    _kr_set("pp_client_secret", secret.strip())
    _write_settings({"pp_sandbox": sandbox})


def load_paypal_settings() -> tuple[str, str, bool]:
    client_id = _kr_get("pp_client_id")
    secret    = _kr_get("pp_client_secret")
    # One-time migration from old JSON storage
    if not client_id or not secret:
        s = load_settings()
        if not client_id and s.get("pp_client_id"):
            client_id = s["pp_client_id"]
            try:
                _kr_set("pp_client_id", client_id)
            except KeyError:
                pass
        if not secret and s.get("pp_secret"):
            secret = s["pp_secret"]
            try:
                _kr_set("pp_client_secret", secret)
            except KeyError:
                pass
        if s.get("pp_client_id") or s.get("pp_secret"):
            _write_settings({})
    sandbox = load_settings().get("pp_sandbox", False)
    return client_id, secret, sandbox
