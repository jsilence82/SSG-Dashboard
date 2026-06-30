"""Persisted user settings — column mappings, capacity overrides, API credentials."""

import json
import logging
import os
from datetime import datetime, timezone

import streamlit as st

from ..config import SETTINGS_FILE

_SERVICE = "ssg_dashboard"

# Graceful keyring import — not available on Linux without a secret service backend
try:
    import keyring
    from keyring.errors import NoKeyringError
    _keyring_ok = True
except Exception:
    _keyring_ok = False


def _is_production() -> bool:
    """True when running on Streamlit Community Cloud or with SSG_PRODUCTION=true."""
    if os.environ.get("SSG_PRODUCTION", "").lower() == "true":
        return True
    try:
        return bool(st.secrets)
    except Exception:
        return False


def get_credential(key: str) -> str:
    """
    Resolve a credential. Resolution order:
      1. st.secrets  (Streamlit Community Cloud / local .streamlit/secrets.toml)
      2. Environment variable (uppercase key name)
      3. keyring     (local dev fallback)
    Returns an empty string when not found anywhere.
    """
    # 1. Streamlit secrets
    try:
        value = st.secrets.get(key.lower())
        if value:
            return str(value)
    except Exception:
        pass

    # 2. Environment variable
    env_val = os.environ.get(key.upper())
    if env_val:
        return env_val

    # 3. keyring (local only)
    if _keyring_ok:
        try:
            return keyring.get_password(_SERVICE, key) or ""
        except Exception:
            pass

    return ""


def set_credential(key: str, value: str) -> None:
    """
    Persist a credential locally. In production (secrets available) this is a no-op —
    credentials are managed via Streamlit secrets or environment variables.
    Locally, writes to the OS keyring. Raises KeyError if no keyring backend is available.
    """
    if _is_production():
        logging.warning("set_credential called in production mode; ignoring.")
        return

    if _keyring_ok:
        try:
            keyring.set_password(_SERVICE, key, value)
            return
        except Exception:
            pass

    raise KeyError(
        "No secure credential store is available on this system. "
        "On Windows, ensure pywin32-ctypes is installed: "
        "pip install pywin32-ctypes"
    )


# ── Non-secret settings (JSON file) ──────────────────────────────────────────

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


# ── Ticket Tailor credentials ────────────────────────────────────────────────

def save_api_key(api_key: str) -> None:
    set_credential("tt_api_key", api_key.strip())


def load_api_key() -> str:
    key = get_credential("tt_api_key")
    if key:
        return key
    # One-time migration: move key from old JSON storage into keychain
    old = load_settings().get("api_key", "")
    if old:
        try:
            set_credential("tt_api_key", old)
            _write_settings({})
        except KeyError:
            pass
    return old


# ── Column mapping & capacity ────────────────────────────────────────────────

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


def save_performance_dates(performance_dates: dict) -> None:
    _write_settings({"performance_dates": {k: v for k, v in performance_dates.items() if v}})


def load_performance_dates() -> dict:
    return load_settings().get("performance_dates", {})


# ── PayPal credentials ───────────────────────────────────────────────────────

def save_paypal_settings(client_id: str, secret: str, sandbox: bool) -> None:
    set_credential("pp_client_id", client_id.strip())
    set_credential("pp_client_secret", secret.strip())
    _write_settings({"pp_sandbox": sandbox})


def load_paypal_settings() -> tuple[str, str, bool]:
    client_id = get_credential("pp_client_id")
    secret    = get_credential("pp_client_secret")
    # One-time migration from old JSON storage
    if not client_id or not secret:
        s = load_settings()
        if not client_id and s.get("pp_client_id"):
            client_id = s["pp_client_id"]
            try:
                set_credential("pp_client_id", client_id)
            except KeyError:
                pass
        if not secret and s.get("pp_secret"):
            secret = s["pp_secret"]
            try:
                set_credential("pp_client_secret", secret)
            except KeyError:
                pass
        if s.get("pp_client_id") or s.get("pp_secret"):
            _write_settings({})
    sandbox = load_settings().get("pp_sandbox", False)
    return client_id, secret, sandbox
