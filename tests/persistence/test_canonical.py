import json
from datetime import datetime, timezone, timedelta

import pandas as pd
import pytest

import ssg_dashboard.persistence.canonical as mod


@pytest.fixture
def cache_file(tmp_path, monkeypatch):
    path = tmp_path / "ssg_cache.json"
    monkeypatch.setattr(mod, "CACHE_FILE", path)
    return path


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "show":                  ["Show A", "Show B"],
        "category":              ["Adult",  "Child"],
        "quantity":              [2.0,      1.0],
        "revenue":               [28.0,     7.0],
        "date":                  pd.to_datetime(["2024-01-10", "2024-01-15"], utc=True),
        "status":                ["complete", "complete"],
        "email":                 ["a@example.com", "b@example.com"],
        "buyer_name":            ["alice", "bob"],
        "buyer_id":              ["a@example.com", "b@example.com"],
        "occurrence":            ["evt1", "evt2"],
        "performance_date":      pd.to_datetime(["2024-02-01", "2024-02-08"], utc=True),
        "paypal_txn_id":         ["PP001", "PP002"],
        "_order_payment_type":   ["paypal", "paypal"],
        "_order_refund_amount":  [0, 0],
    })


class TestSaveLoadRoundtrip:
    def test_data_preserved(self, cache_file, sample_df):
        mod.save_cache(sample_df, {"Show A": 100})
        df, saved_at, capacity, perf_dates = mod.load_cache()
        assert list(df["show"]) == ["Show A", "Show B"]
        assert list(df["category"]) == ["Adult", "Child"]
        assert capacity == {"Show A": 100}
        assert saved_at is not None

    def test_performance_dates_preserved(self, cache_file, sample_df):
        dates = {"Show A": {"tickets_available_at": "2024-01-01", "tickets_unavailable_at": "2024-02-01"}}
        mod.save_cache(sample_df, {}, dates)
        _, _, _, perf_dates = mod.load_cache()
        assert perf_dates == dates

    def test_dates_restored_as_datetime(self, cache_file, sample_df):
        mod.save_cache(sample_df)
        df, _, _, _ = mod.load_cache()
        assert pd.api.types.is_datetime64_any_dtype(df["date"])
        assert pd.api.types.is_datetime64_any_dtype(df["performance_date"])

    def test_numeric_columns_restored(self, cache_file, sample_df):
        mod.save_cache(sample_df)
        df, _, _, _ = mod.load_cache()
        assert df["quantity"].dtype.kind in ("f", "i")
        assert df["revenue"].dtype.kind in ("f", "i")

    def test_capacity_defaults_to_empty_when_none(self, cache_file, sample_df):
        mod.save_cache(sample_df, None)
        _, _, capacity, perf_dates = mod.load_cache()
        assert capacity == {}
        assert perf_dates == {}


class TestLoadEdgeCases:
    def test_missing_file_returns_none(self, cache_file):
        df, saved_at, capacity, perf_dates = mod.load_cache()
        assert df is None
        assert saved_at is None
        assert capacity == {}
        assert perf_dates == {}

    def test_corrupted_json_returns_none(self, cache_file):
        cache_file.write_text("not valid json", encoding="utf-8")
        df, saved_at, capacity, perf_dates = mod.load_cache()
        assert df is None

    def test_backfills_missing_columns_from_old_cache(self, cache_file):
        old_payload = {
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "is_canonical": True,
            "records": [{"show": "Show A", "category": "Adult", "quantity": 1, "revenue": 10.0,
                         "date": "2024-01-10", "status": "complete"}],
            "capacity_by_show": {},
        }
        cache_file.write_text(json.dumps(old_payload), encoding="utf-8")
        df, _, _, _ = mod.load_cache()
        assert "performance_date" in df.columns
        assert "email" in df.columns
        assert "occurrence" in df.columns
        assert "buyer_name" in df.columns
        assert "paypal_txn_id" in df.columns
        assert "_order_payment_type" in df.columns
        assert "_order_refund_amount" in df.columns


class TestCacheAgeLabel:
    def test_none_returns_unknown_age(self):
        assert mod.cache_age_label(None) == "unknown age"

    def test_invalid_string_returns_unknown_age(self):
        assert mod.cache_age_label("not-a-date") == "unknown age"

    def test_recent_returns_under_1_hour(self):
        recent = datetime.now(timezone.utc).isoformat()
        assert mod.cache_age_label(recent) == "< 1 hour ago"

    def test_2_hours_ago(self):
        two_hours = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        assert mod.cache_age_label(two_hours) == "2 hours ago"

    def test_exactly_1_hour(self):
        one_hour = (datetime.now(timezone.utc) - timedelta(hours=1, minutes=1)).isoformat()
        assert mod.cache_age_label(one_hour) == "1 hour ago"

    def test_more_than_24_hours_returns_days(self):
        two_days = (datetime.now(timezone.utc) - timedelta(hours=49)).isoformat()
        assert mod.cache_age_label(two_days) == "2 day(s) ago"
