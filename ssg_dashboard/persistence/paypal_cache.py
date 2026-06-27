"""
Smart cache for PayPal transactions.

Persists to data/paypal_cache.json and tracks the date range covered.
Only calls the PayPal API for date portions not already on disk.
"""

import json
from datetime import date, datetime, timedelta

from ..config import DATA_DIR
from ..api.paypal import pp_fetch_transactions

PP_CACHE_FILE = DATA_DIR / "paypal_cache.json"


def load_paypal_cache() -> tuple[list[dict], date, date, str] | None:
    # covered_start/end are the query boundaries, not the min/max transaction dates
    if not PP_CACHE_FILE.exists():
        return None
    try:
        payload = json.loads(PP_CACHE_FILE.read_text(encoding="utf-8"))
        return (
            payload.get("transactions", []),
            date.fromisoformat(payload["covered_start"]),
            date.fromisoformat(payload["covered_end"]),
            payload.get("saved_at", ""),
        )
    except Exception:
        return None


def save_paypal_cache(
    transactions: list[dict],
    covered_start: date,
    covered_end: date,
) -> None:
    payload = {
        "saved_at":      datetime.now().isoformat(),
        "covered_start": covered_start.isoformat(),
        "covered_end":   covered_end.isoformat(),
        "transactions":  transactions,
    }
    PP_CACHE_FILE.write_text(json.dumps(payload, default=str), encoding="utf-8")


def clear_paypal_cache() -> None:
    if PP_CACHE_FILE.exists():
        PP_CACHE_FILE.unlink()


def _fetch(token: str, start: date, end: date, sandbox: bool) -> list[dict]:
    return pp_fetch_transactions(
        token,
        datetime.combine(start, datetime.min.time()),
        datetime.combine(end,   datetime.min.time()),
        sandbox,
    )


def _dedup(txns: list[dict]) -> list[dict]:
    seen, out = set(), []
    for t in txns:
        tid = t.get("txn_id", "")
        if tid not in seen:
            seen.add(tid)
            out.append(t)
    return out


def get_paypal_transactions(
    access_token: str,
    req_start: date,
    req_end: date,
    sandbox: bool = False,
    force_refresh: bool = False,
) -> list[dict]:
    """Return transactions for [req_start, req_end], fetching only uncached date gaps."""
    cached = None if force_refresh else load_paypal_cache()

    if cached is None:
        txns = _fetch(access_token, req_start, req_end, sandbox)
        save_paypal_cache(txns, req_start, req_end)
        return _in_range(txns, req_start, req_end)

    cached_txns, c_start, c_end, _ = cached

    if req_start >= c_start and req_end <= c_end:
        return _in_range(cached_txns, req_start, req_end)

    all_txns  = list(cached_txns)
    new_start = c_start
    new_end   = c_end

    if req_start < c_start:
        earlier   = _fetch(access_token, req_start, c_start - timedelta(days=1), sandbox)
        all_txns  = earlier + all_txns
        new_start = req_start

    if req_end > c_end:
        later    = _fetch(access_token, c_end + timedelta(days=1), req_end, sandbox)
        all_txns = all_txns + later
        new_end  = req_end

    merged = _dedup(all_txns)
    save_paypal_cache(merged, new_start, new_end)
    return _in_range(merged, req_start, req_end)


def _in_range(txns: list[dict], start: date, end: date) -> list[dict]:
    s, e = start.isoformat(), end.isoformat()
    return [t for t in txns if s <= (t.get("date") or "") <= e]


def cache_status_label() -> str | None:
    result = load_paypal_cache()
    if result is None:
        return None
    txns, c_start, c_end, saved_at = result
    try:
        dt    = datetime.fromisoformat(saved_at)
        delta = datetime.now() - dt
        h     = int(delta.total_seconds() // 3600)
        age   = f"{h}h ago" if h >= 1 else "< 1h ago"
    except Exception:
        age = "unknown age"
    return f"{len(txns):,} transactions · covers {c_start} → {c_end} · saved {age}"
