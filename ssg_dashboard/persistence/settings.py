"""Persisted user settings — column mappings, capacity overrides, API credentials."""

import json
from datetime import datetime, timezone

import keyring

from ..config import SETTINGS_FILE

_SERVICE = "ssg_dashboard"


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
    keyring.set_password(_SERVICE, "tt_api_key", api_key.strip())


def load_api_key() -> str:
    key = keyring.get_password(_SERVICE, "tt_api_key")
    if key:
        return key
    # One-time migration: move key from old JSON storage into keychain
    old = load_settings().get("api_key", "")
    if old:
        keyring.set_password(_SERVICE, "tt_api_key", old)
        _write_settings({})
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
    keyring.set_password(_SERVICE, "pp_client_id", client_id.strip())
    keyring.set_password(_SERVICE, "pp_client_secret", secret.strip())
    _write_settings({"pp_sandbox": sandbox})


def load_paypal_settings() -> tuple[str, str, bool]:
    client_id = keyring.get_password(_SERVICE, "pp_client_id") or ""
    secret    = keyring.get_password(_SERVICE, "pp_client_secret") or ""
    # One-time migration from old JSON storage
    if not client_id or not secret:
        s = load_settings()
        if not client_id and s.get("pp_client_id"):
            client_id = s["pp_client_id"]
            keyring.set_password(_SERVICE, "pp_client_id", client_id)
        if not secret and s.get("pp_secret"):
            secret = s["pp_secret"]
            keyring.set_password(_SERVICE, "pp_client_secret", secret)
        if s.get("pp_client_id") or s.get("pp_secret"):
            _write_settings({})
    sandbox = load_settings().get("pp_sandbox", False)
    return client_id, secret, sandbox
