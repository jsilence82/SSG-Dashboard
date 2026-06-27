"""Persistent disk cache for raw Ticket Tailor API data."""

import json
from datetime import datetime

from ..config import DATA_DIR

TT_RAW_CACHE_FILE = DATA_DIR / "tt_raw_cache.json"


def save_tt_raw_cache(
    tickets_raw: list[dict],
    events_raw: list[dict],
    orders_raw: list[dict],
    capacity_by_show: dict,
) -> None:
    payload = {
        "saved_at":        datetime.now().isoformat(),
        "tickets":         tickets_raw,
        "events":          events_raw,
        "orders":          orders_raw,
        "capacity_by_show": capacity_by_show,
    }
    TT_RAW_CACHE_FILE.write_text(json.dumps(payload, default=str), encoding="utf-8")


def load_tt_raw_cache() -> tuple[list, list, list, dict, str] | None:
    if not TT_RAW_CACHE_FILE.exists():
        return None
    try:
        payload = json.loads(TT_RAW_CACHE_FILE.read_text(encoding="utf-8"))
        return (
            payload.get("tickets", []),
            payload.get("events", []),
            payload.get("orders", []),
            payload.get("capacity_by_show", {}),
            payload.get("saved_at", ""),
        )
    except Exception:
        return None


def tt_cache_status_label() -> str | None:
    result = load_tt_raw_cache()
    if result is None:
        return None
    tickets, _, _, _, saved_at = result
    try:
        dt    = datetime.fromisoformat(saved_at)
        delta = datetime.now() - dt
        h     = int(delta.total_seconds() // 3600)
        age   = f"{h}h ago" if h >= 1 else "< 1h ago"
    except Exception:
        age = "unknown age"
    return f"{len(tickets):,} tickets · fetched {age}"
