"""Local cache of canonical ticket data + capacity snapshot."""

import json
from datetime import datetime, timezone

import pandas as pd

from ..config import CACHE_FILE


def save_cache(canonical_df: pd.DataFrame, capacity_by_show: dict | None = None) -> None:
    df_copy = canonical_df.copy()
    for date_col in ("date", "performance_date"):
        if date_col in df_copy.columns:
            df_copy[date_col] = df_copy[date_col].astype(str)
    payload = {
        "saved_at":         datetime.now(timezone.utc).isoformat(),
        "is_canonical":     True,
        "records":          df_copy.to_dict(orient="records"),
        "capacity_by_show": capacity_by_show or {},
    }
    CACHE_FILE.write_text(json.dumps(payload, default=str), encoding="utf-8")


def load_cache() -> tuple[pd.DataFrame | None, str | None, dict]:
    if not CACHE_FILE.exists():
        return None, None, {}
    try:
        payload = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        df = pd.DataFrame(payload.get("records", []))
        if df.empty:
            return None, None, {}
        for date_col in ("date", "performance_date"):
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce", utc=True)
        for col in ("quantity", "revenue"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        # Backfill columns added after old caches were written
        if "performance_date" not in df.columns:
            df["performance_date"] = pd.NaT
        if "email" not in df.columns:
            df["email"] = ""
        if "occurrence" not in df.columns:
            df["occurrence"] = ""
        if "buyer_name" not in df.columns:
            df["buyer_name"] = ""
        if "buyer_id" not in df.columns:
            df["buyer_id"] = df["email"]
        if "paypal_txn_id" not in df.columns:
            df["paypal_txn_id"] = ""
        if "_order_payment_type" not in df.columns:
            df["_order_payment_type"] = ""
        if "_order_refund_amount" not in df.columns:
            df["_order_refund_amount"] = 0
        return df, payload.get("saved_at"), payload.get("capacity_by_show", {})
    except Exception:
        return None, None, {}


def cache_age_label(saved_at: str | None) -> str:
    if not saved_at:
        return "unknown age"
    try:
        dt = datetime.fromisoformat(saved_at)
        delta = datetime.now(timezone.utc) - dt
        h = int(delta.total_seconds() // 3600)
        if h < 1:   return "< 1 hour ago"
        if h == 1:  return "1 hour ago"
        if h < 24:  return f"{h} hours ago"
        return f"{h // 24} day(s) ago"
    except Exception:
        return "unknown age"
