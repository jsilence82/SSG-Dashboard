"""Shared constants and file paths."""

from pathlib import Path

TT_BASE_URL = "https://api.tickettailor.com/v1"
PP_BASE_URL = "https://api.paypal.com"

DATA_DIR      = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
CACHE_FILE    = DATA_DIR / "ssg_cache.json"
SETTINGS_FILE = DATA_DIR / "ssg_settings.json"

CANONICAL_FIELDS = {
    "show":             "Show / Event name (required)",
    "category":         "Ticket category / type (required)",
    "quantity":         "Quantity (optional — leave unset if every row = 1 ticket)",
    "revenue":          "Price / revenue per row (optional)",
    "date":             "Sale date (optional — when the ticket was purchased)",
    "status":           "Status (optional — exclude voided/refunded rows)",
    "email":            "Buyer email (optional — for repeat buyer analysis)",
    "buyer_name":       "Buyer name (optional — fallback identifier when email is missing)",
    "occurrence":       "Occurrence ID (optional — groups tickets by night)",
    "performance_date": "Performance date (optional — for day-of-week analysis)",
    "paypal_txn_id":    "PayPal Transaction ID (auto-populated from TT orders on refresh)",
}

DOW_ORDER = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
