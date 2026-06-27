import pandas as pd
import pytest


@pytest.fixture
def sample_raw_df():
    """Raw DataFrame that resembles post-TT-API-processing data."""
    return pd.DataFrame({
        "show_name":             ["Show A", "Show A", "Show B"],
        "ticket_type":           ["Adult",  "Child",  "Adult"],
        "qty":                   [2,        1,        3],
        "price":                 [2800,     700,      4500],  # cents
        "sale_date":             ["2024-01-10", "2024-01-10", "2024-01-15"],
        "ticket_status":         ["complete", "complete", "void"],
        "buyer_email":           ["a@example.com", "b@example.com", "c@example.com"],
        "last_name":             ["Alice", "Bob", "Carol"],
        "event_id":              ["evt1", "evt1", "evt2"],
        "_paypal_txn_id":        ["PP001", "PP001", "PP002"],
        "_order_payment_type":   ["paypal", "paypal", "paypal"],
        "_order_refund_amount":  [0, 0, 0],
    })


@pytest.fixture
def base_mapping():
    return {
        "show":             "show_name",
        "category":         "ticket_type",
        "quantity":         "qty",
        "revenue":          "price",
        "date":             "sale_date",
        "status":           "ticket_status",
        "email":            "buyer_email",
        "buyer_name":       "last_name",
        "occurrence":       None,
        "performance_date": None,
        "paypal_txn_id":    None,
    }
