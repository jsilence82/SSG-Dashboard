"""Ticket Tailor API client."""

import base64
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st

from ..config import TT_BASE_URL
from ..persistence.tt_cache import load_tt_raw_cache, save_tt_raw_cache


def tt_headers(api_key: str) -> dict:
    token = base64.b64encode(f"{api_key}:".encode()).decode()
    return {"Accept": "application/json", "Authorization": f"Basic {token}"}


def tt_ping(api_key: str) -> tuple[bool, str]:
    try:
        r = requests.get(f"{TT_BASE_URL}/events", headers=tt_headers(api_key),
                         params={"limit": 1}, timeout=15)
        if r.status_code == 200:  return True,  "Connected."
        if r.status_code == 401:  return False, "Unauthorized — check the key."
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except requests.RequestException as exc:
        return False, f"Network error: {exc}"


def _extract_records(payload):
    if isinstance(payload, list):  return payload
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), list):  return payload["data"]
        for v in payload.values():
            if isinstance(v, list):  return v
    return []


def tt_fetch_all(api_key: str, endpoint: str, max_pages: int = 200,
                 progress_label: str = "") -> list[dict]:
    records, params = [], {"limit": 100}
    progress = st.progress(0.0, text=progress_label) if progress_label else None
    starting_after = None
    for page in range(max_pages):
        if starting_after:
            params["starting_after"] = starting_after
        r = requests.get(f"{TT_BASE_URL}/{endpoint}", headers=tt_headers(api_key),
                         params=params, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"API error on /{endpoint}: {r.status_code} {r.text[:300]}")
        page_records = _extract_records(r.json())
        records.extend(page_records)
        if progress:
            progress.progress(min(0.95, 0.1 + page * 0.05), text=progress_label)
        if len(page_records) < params["limit"]:  break
        starting_after = page_records[-1].get("id")
        if not starting_after:  break
    if progress:
        progress.progress(1.0, text=f"{progress_label} done ({len(records)} records)")
        progress.empty()
    return records


def _process_tt_raw(
    tickets_raw: list[dict],
    events_raw: list[dict],
    orders_raw: list[dict],
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Convert raw TT API lists into DataFrames.  Used by both the live API path
    and the disk-cache load path so processing logic is never duplicated.
    """
    events_df  = pd.json_normalize(events_raw,  sep=".") if events_raw  else pd.DataFrame()
    tickets_df = pd.json_normalize(tickets_raw, sep=".") if tickets_raw else pd.DataFrame()

    event_id_col = next((c for c in tickets_df.columns
                         if c.lower() in ("event_id", "event.id")), None)
    name_col  = next((c for c in events_df.columns if c.lower() in ("name", "title")), None)
    id_col    = next((c for c in events_df.columns if c.lower() == "id"), None)
    start_col = next(
        (c for c in events_df.columns
         if c.lower() in ("start.unix", "start_unix", "start_timestamp")
         or ("start" in c.lower() and "unix" in c.lower())),
        next(
            (c for c in events_df.columns
             if c.lower() in ("start", "start_date", "start.date",
                              "start_time", "start.time")),
            None,
        ),
    )

    if orders_raw:
        order_txn_map        = {}
        order_pm_type_map    = {}
        order_refund_map     = {}
        order_total_paid_map = {}
        for o in orders_raw:
            oid = o.get("id")
            if not oid:
                continue
            order_txn_map[oid]        = o.get("txn_id") or ""
            order_pm_type_map[oid]    = (o.get("payment_method") or {}).get("type", "")
            order_refund_map[oid]     = o.get("refund_amount") or 0
            order_total_paid_map[oid] = o.get("total_paid") or 0

        order_id_col = next(
            (c for c in tickets_df.columns if c.lower() == "order_id"), None
        )
        if order_id_col and not tickets_df.empty:
            tickets_df["_paypal_txn_id"]       = tickets_df[order_id_col].map(order_txn_map).fillna("")
            tickets_df["_order_payment_type"]  = tickets_df[order_id_col].map(order_pm_type_map).fillna("")
            tickets_df["_order_refund_amount"] = tickets_df[order_id_col].map(order_refund_map).fillna(0)

            # total_paid is order-level (e.g. 0 when an order's tickets were transferred
            # elsewhere despite a non-zero listed price); split evenly across the order's
            # tickets so per-ticket sums stay additive back to the order's real total_paid.
            tickets_per_order = tickets_df[order_id_col].value_counts()
            order_total_paid  = tickets_df[order_id_col].map(order_total_paid_map).fillna(0)
            order_ticket_count = tickets_df[order_id_col].map(tickets_per_order).fillna(1)
            tickets_df["_order_total_paid"] = order_total_paid / order_ticket_count

    if event_id_col and id_col and not events_df.empty:
        join_cols  = [id_col]
        rename_map = {id_col: "_event_id"}
        if name_col:  join_cols.append(name_col);  rename_map[name_col]  = "_event_name"
        if start_col: join_cols.append(start_col); rename_map[start_col] = "_performance_start"
        lookup     = events_df[join_cols].rename(columns=rename_map)
        tickets_df = tickets_df.merge(lookup, left_on=event_id_col,
                                      right_on="_event_id", how="left")

    capacity_by_show: dict[str, int] = {}
    cap_col = next((c for c in events_df.columns if "capacity" in c.lower()), None)
    if name_col and cap_col and not events_df.empty:
        for _, row in events_df.iterrows():
            cap = pd.to_numeric(row.get(cap_col, 0), errors="coerce")
            if pd.notna(cap) and cap > 0:
                capacity_by_show[str(row[name_col])] = int(cap)

    return tickets_df, events_df, capacity_by_show


def _tt_to_iso(value) -> str | None:
    """Normalise a Ticket Tailor date field into an ISO 8601 string.

    TT date fields are nested objects with 'iso', 'formatted', 'date', and
    'unix' keys; 'iso' is preferred since it preserves the event's own
    timezone instead of collapsing to UTC. Plain unix ints/strings (e.g. from
    older cached payloads) are also handled.
    """
    if isinstance(value, dict):
        for key in ("iso", "formatted", "date"):
            if value.get(key):
                return value[key]
        value = value.get("unix")
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    if isinstance(value, str) and value:
        return value
    return None


def _process_event_series(event_series_raw: list[dict]) -> dict[str, dict]:
    """Map each event series (show) name to its ticket sale window —
    when tickets went on sale and when they came offline (event ended)."""
    performance_dates: dict[str, dict] = {}
    for series in event_series_raw:
        name = series.get("name")
        if not name:
            continue
        start = _tt_to_iso(series.get("tickets_available_at"))
        end   = _tt_to_iso(series.get("tickets_unavailable_at"))
        if start or end:
            performance_dates[name] = {"tickets_available_at": start, "tickets_unavailable_at": end}
    return performance_dates


@st.cache_data(show_spinner=False, ttl=900)
def _fetch_raw(api_key: str) -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]:
    events_raw       = tt_fetch_all(api_key, "events",         progress_label="Fetching events…")
    tickets_raw      = tt_fetch_all(api_key, "issued_tickets", progress_label="Fetching tickets…")
    orders_raw       = tt_fetch_all(api_key, "orders",         progress_label="Fetching orders…")
    event_series_raw = tt_fetch_all(api_key, "event_series",   progress_label="Fetching event series…")

    tickets_df, events_df, capacity_by_show = _process_tt_raw(tickets_raw, events_raw, orders_raw)
    performance_dates_by_show = _process_event_series(event_series_raw)

    # Persist raw data so the next session can skip this API call
    save_tt_raw_cache(tickets_raw, events_raw, orders_raw, capacity_by_show,
                       event_series_raw, performance_dates_by_show)

    return tickets_df, events_df, capacity_by_show, performance_dates_by_show


def fetch_and_store(api_key: str) -> tuple[bool, str]:
    try:
        tickets_df, events_df, capacity_by_show, performance_dates_by_show = _fetch_raw(api_key)
        if tickets_df.empty:
            return False, "No issued tickets returned."
        st.session_state["raw_df"]                 = tickets_df
        st.session_state["raw_source"]              = "api"
        st.session_state["api_capacity"]            = capacity_by_show
        st.session_state["api_performance_dates"]   = performance_dates_by_show
        return True, f"Fetched {len(tickets_df)} rows across {len(events_df)} events."
    except RuntimeError as exc:
        return False, str(exc)


def refresh_from_api(api_key: str) -> tuple[bool, str]:
    _fetch_raw.clear()
    return fetch_and_store(api_key)


def load_from_tt_cache() -> tuple[bool, str]:
    result = load_tt_raw_cache()
    if result is None:
        return False, "No TT raw cache found on disk."
    (tickets_raw, events_raw, orders_raw, capacity_by_show,
     _event_series_raw, performance_dates_by_show, saved_at) = result
    try:
        tickets_df, _, _ = _process_tt_raw(tickets_raw, events_raw, orders_raw)
        if tickets_df.empty:
            return False, "TT cache exists but contains no ticket rows."
        st.session_state["raw_df"]                 = tickets_df
        st.session_state["raw_source"]              = "api"
        st.session_state["api_capacity"]            = capacity_by_show
        st.session_state["api_performance_dates"]   = performance_dates_by_show
        return True, f"Loaded {len(tickets_df)} rows from TT cache (saved {saved_at[:10]})."
    except Exception as exc:
        return False, f"Could not process TT cache: {exc}"
