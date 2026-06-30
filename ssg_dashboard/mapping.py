"""Column mapping UI and canonical dataframe construction."""

import pandas as pd
import streamlit as st

from .config import CANONICAL_FIELDS


def guess_column(columns: list[str], keywords: list[str]) -> str | None:
    low = {c: c.lower() for c in columns}
    for kw in keywords:
        for col, lc in low.items():
            if kw in lc:  return col
    return None


def mapping_ui(df: pd.DataFrame, key_prefix: str, saved: dict) -> dict:
    columns, opts_opt = list(df.columns), ["(none)"] + list(df.columns)
    saved_map = saved.get("mapping", {})
    guesses = {
        "show":       guess_column(columns, ["show", "event", "production", "stück", "titel", "title", "_event_name"]),
        "category":   guess_column(columns, ["category", "type", "kategorie", "ticket_type", "tarif"]),
        "quantity":   guess_column(columns, ["qty", "quantity", "anzahl", "menge"]),
        "revenue":    guess_column(columns, ["price", "revenue", "amount", "preis", "umsatz", "value"]),
        "date":       guess_column(columns, ["issued_at", "date", "datum", "created"]),
        "status":     guess_column(columns, ["status", "state"]),
        "email":            guess_column(columns, ["buyer_email", "email", "e-mail", "mail"]),
        "buyer_name":       guess_column(columns, ["full_name", "last_name", "surname",
                                                   "nachname", "buyer_name", "name"]),
        "occurrence":       guess_column(columns, ["event_id", "event_occurrence_id",
                                                   "occurrence_id", "occurrence", "night"]),
        "performance_date": guess_column(columns, ["_performance_start", "performance_start",
                                                   "start", "performance_date", "show_date",
                                                   "event_date", "vorstellung_datum"]),
        "paypal_txn_id":    guess_column(columns, ["_paypal_txn_id", "paypal_transaction_id",
                                                   "paypal_txn", "txn_id", "transaction_id"]),
    }
    mapping, c1, c2 = {}, *st.columns(2)
    for i, (field, label) in enumerate(CANONICAL_FIELDS.items()):
        tc, required = (c1 if i % 2 == 0 else c2), field in ("show", "category")
        opts = columns if required else opts_opt
        saved_val = saved_map.get(field)
        default = (saved_val if saved_val and saved_val in opts else
                   guesses[field] if guesses[field] and guesses[field] in opts else
                   (opts[0] if required else "(none)"))
        with tc:
            choice = st.selectbox(label, opts, index=opts.index(default) if default in opts else 0,
                                  key=f"{key_prefix}_{field}")
        mapping[field] = None if choice == "(none)" else choice
    return mapping


def _parse_date_column(col: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(col):
        return pd.to_datetime(col, unit="s", utc=True, errors="coerce")
    numeric = pd.to_numeric(col, errors="coerce")
    if numeric.notna().sum() / max(len(col), 1) > 0.8:
        return pd.to_datetime(numeric, unit="s", utc=True, errors="coerce")
    return pd.to_datetime(col, errors="coerce", utc=True)


def build_canonical(df: pd.DataFrame, mapping: dict,
                    prices_in_cents: bool, revenue_is_per_unit: bool) -> pd.DataFrame:
    out = pd.DataFrame()
    out["show"]     = df[mapping["show"]].astype(str)
    out["category"] = df[mapping["category"]].astype(str)
    out["quantity"]  = pd.to_numeric(df[mapping["quantity"]], errors="coerce").fillna(1) \
                       if mapping.get("quantity") else 1.0
    if mapping.get("revenue"):
        rev = pd.to_numeric(df[mapping["revenue"]], errors="coerce").fillna(0)
        rev = rev / 100.0 if prices_in_cents else rev
        out["revenue"] = rev * out["quantity"] if revenue_is_per_unit else rev
    else:
        out["revenue"] = 0.0
    out["date"]       = _parse_date_column(df[mapping["date"]]) if mapping.get("date") else pd.NaT
    out["status"]     = df[mapping["status"]].astype(str) if mapping.get("status") else "unknown"
    out["email"]      = df[mapping["email"]].astype(str).str.lower().str.strip() \
                        if mapping.get("email") else ""
    out["buyer_name"] = df[mapping["buyer_name"]].astype(str).str.lower().str.strip() \
                        if mapping.get("buyer_name") else ""
    out["buyer_id"] = out["email"].where(out["email"].astype(bool), out["buyer_name"])
    if mapping.get("occurrence") and mapping["occurrence"] in df.columns:
        out["occurrence"] = df[mapping["occurrence"]].astype(str)
    elif "event_id" in df.columns:
        out["occurrence"] = df["event_id"].astype(str)
    else:
        out["occurrence"] = ""
    if mapping.get("performance_date") and mapping["performance_date"] in df.columns:
        out["performance_date"] = _parse_date_column(df[mapping["performance_date"]])
    elif "_performance_start" in df.columns:
        out["performance_date"] = _parse_date_column(df["_performance_start"])
    else:
        out["performance_date"] = pd.NaT
    if mapping.get("paypal_txn_id") and mapping["paypal_txn_id"] in df.columns:
        out["paypal_txn_id"] = df[mapping["paypal_txn_id"]].astype(str).str.strip()
    elif "_paypal_txn_id" in df.columns:
        out["paypal_txn_id"] = df["_paypal_txn_id"].astype(str).str.strip()
    else:
        out["paypal_txn_id"] = ""

    # Order-level payment metadata — sourced from TT orders join, not user-mapped
    out["_order_payment_type"]  = df["_order_payment_type"].astype(str)  \
                                  if "_order_payment_type"  in df.columns else ""
    out["_order_refund_amount"] = pd.to_numeric(df["_order_refund_amount"], errors="coerce").fillna(0) \
                                  if "_order_refund_amount" in df.columns else 0
    return out
