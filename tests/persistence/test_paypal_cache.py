from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

import ssg_dashboard.persistence.paypal_cache as mod


@pytest.fixture
def cache_file(tmp_path, monkeypatch):
    path = tmp_path / "paypal_cache.json"
    monkeypatch.setattr(mod, "PP_CACHE_FILE", path)
    return path


def _make_txn(txn_id, txn_date, gross=10.0):
    return {"txn_id": txn_id, "date": txn_date, "gross": gross, "fee": -0.3, "net": gross - 0.3}


TXNS = [
    _make_txn("T1", "2024-01-05"),
    _make_txn("T2", "2024-01-15"),
    _make_txn("T3", "2024-01-25"),
]


class TestInRange:
    def test_returns_transactions_within_range(self):
        result = mod._in_range(TXNS, date(2024, 1, 10), date(2024, 1, 20))
        assert len(result) == 1
        assert result[0]["txn_id"] == "T2"

    def test_inclusive_on_both_ends(self):
        result = mod._in_range(TXNS, date(2024, 1, 5), date(2024, 1, 25))
        assert len(result) == 3

    def test_returns_empty_when_nothing_in_range(self):
        result = mod._in_range(TXNS, date(2024, 2, 1), date(2024, 2, 28))
        assert result == []

    def test_empty_input_returns_empty(self):
        assert mod._in_range([], date(2024, 1, 1), date(2024, 1, 31)) == []


class TestDedup:
    def test_removes_duplicate_txn_ids(self):
        dupes = [_make_txn("T1", "2024-01-05"), _make_txn("T1", "2024-01-05")]
        result = mod._dedup(dupes)
        assert len(result) == 1

    def test_keeps_first_occurrence(self):
        dupes = [_make_txn("T1", "2024-01-05", gross=10.0),
                 _make_txn("T1", "2024-01-05", gross=99.0)]
        result = mod._dedup(dupes)
        assert result[0]["gross"] == 10.0

    def test_preserves_all_unique(self):
        result = mod._dedup(TXNS)
        assert len(result) == 3


class TestSaveLoadRoundtrip:
    def test_transactions_and_dates_preserved(self, cache_file):
        mod.save_paypal_cache(TXNS, date(2024, 1, 1), date(2024, 1, 31))
        result = mod.load_paypal_cache()
        assert result is not None
        txns, c_start, c_end, saved_at = result
        assert len(txns) == 3
        assert c_start == date(2024, 1, 1)
        assert c_end == date(2024, 1, 31)
        assert saved_at != ""

    def test_missing_file_returns_none(self, cache_file):
        assert mod.load_paypal_cache() is None

    def test_corrupted_file_returns_none(self, cache_file):
        cache_file.write_text("not json", encoding="utf-8")
        assert mod.load_paypal_cache() is None


class TestGetPaypalTransactions:
    def _patch_fetch(self, monkeypatch, return_value):
        monkeypatch.setattr(mod, "_fetch", lambda *a, **kw: return_value)

    def test_no_cache_calls_fetch_and_saves(self, cache_file, monkeypatch):
        fetched = [_make_txn("T1", "2024-01-15")]
        self._patch_fetch(monkeypatch, fetched)

        result = mod.get_paypal_transactions("tok", date(2024, 1, 1), date(2024, 1, 31))

        assert len(result) == 1
        assert mod.load_paypal_cache() is not None

    def test_fully_covered_returns_from_cache_without_fetch(self, cache_file, monkeypatch):
        mod.save_paypal_cache(TXNS, date(2024, 1, 1), date(2024, 1, 31))

        fetch_called = []
        monkeypatch.setattr(mod, "_fetch", lambda *a, **kw: fetch_called.append(1) or [])

        result = mod.get_paypal_transactions("tok", date(2024, 1, 10), date(2024, 1, 20))
        assert fetch_called == []
        assert result[0]["txn_id"] == "T2"

    def test_left_gap_fetches_earlier_period(self, cache_file, monkeypatch):
        mod.save_paypal_cache(TXNS, date(2024, 1, 10), date(2024, 1, 31))

        earlier_txn = [_make_txn("T0", "2024-01-03")]
        fetch_calls = []

        def mock_fetch(token, start, end, sandbox):
            fetch_calls.append((start, end))
            return earlier_txn

        monkeypatch.setattr(mod, "_fetch", mock_fetch)

        mod.get_paypal_transactions("tok", date(2024, 1, 1), date(2024, 1, 31))

        assert len(fetch_calls) == 1
        assert fetch_calls[0][0] == date(2024, 1, 1)

        _, new_start, _, _ = mod.load_paypal_cache()
        assert new_start == date(2024, 1, 1)

    def test_right_gap_fetches_later_period(self, cache_file, monkeypatch):
        mod.save_paypal_cache(TXNS, date(2024, 1, 1), date(2024, 1, 20))

        later_txn = [_make_txn("T4", "2024-01-28")]
        fetch_calls = []

        def mock_fetch(token, start, end, sandbox):
            fetch_calls.append((start, end))
            return later_txn

        monkeypatch.setattr(mod, "_fetch", mock_fetch)

        mod.get_paypal_transactions("tok", date(2024, 1, 1), date(2024, 1, 31))

        assert len(fetch_calls) == 1
        assert fetch_calls[0][1] == date(2024, 1, 31)

        _, _, new_end, _ = mod.load_paypal_cache()
        assert new_end == date(2024, 1, 31)

    def test_force_refresh_bypasses_cache(self, cache_file, monkeypatch):
        mod.save_paypal_cache(TXNS, date(2024, 1, 1), date(2024, 1, 31))

        fetch_called = []
        monkeypatch.setattr(mod, "_fetch", lambda *a, **kw: fetch_called.append(1) or [])

        mod.get_paypal_transactions("tok", date(2024, 1, 10), date(2024, 1, 20), force_refresh=True)
        assert fetch_called != []
