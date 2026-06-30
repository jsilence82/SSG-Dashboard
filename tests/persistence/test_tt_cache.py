import pytest

import ssg_dashboard.persistence.tt_cache as mod


@pytest.fixture
def cache_file(tmp_path, monkeypatch):
    path = tmp_path / "tt_raw_cache.json"
    monkeypatch.setattr(mod, "TT_RAW_CACHE_FILE", path)
    return path


TICKETS       = [{"id": "t1", "event_id": "e1"}, {"id": "t2", "event_id": "e2"}]
EVENTS        = [{"id": "e1", "name": "Show A"}, {"id": "e2", "name": "Show B"}]
ORDERS        = [{"id": "o1", "txn_id": "PP1"}]
CAP           = {"Show A": 100, "Show B": 80}
EVENT_SERIES  = [{"id": "s1", "name": "Show A", "tickets_available_at": 1, "tickets_unavailable_at": 2}]
PERF_DATES    = {"Show A": {"tickets_available_at": "2024-01-01T00:00:00+00:00",
                             "tickets_unavailable_at": "2024-01-02T00:00:00+00:00"}}


class TestSaveLoadRoundtrip:
    def test_all_fields_preserved(self, cache_file):
        mod.save_tt_raw_cache(TICKETS, EVENTS, ORDERS, CAP, EVENT_SERIES, PERF_DATES)
        result = mod.load_tt_raw_cache()
        assert result is not None
        tickets, events, orders, capacity, event_series, perf_dates, saved_at = result
        assert tickets == TICKETS
        assert events == EVENTS
        assert orders == ORDERS
        assert capacity == CAP
        assert event_series == EVENT_SERIES
        assert perf_dates == PERF_DATES
        assert saved_at != ""

    def test_empty_lists_preserved(self, cache_file):
        mod.save_tt_raw_cache([], [], [], {})
        tickets, events, orders, capacity, event_series, perf_dates, _ = mod.load_tt_raw_cache()
        assert tickets == []
        assert events == []
        assert orders == []
        assert capacity == {}
        assert event_series == []
        assert perf_dates == {}


class TestLoadEdgeCases:
    def test_missing_file_returns_none(self, cache_file):
        assert mod.load_tt_raw_cache() is None

    def test_corrupted_json_returns_none(self, cache_file):
        cache_file.write_text("not valid json", encoding="utf-8")
        assert mod.load_tt_raw_cache() is None


class TestTtCacheStatusLabel:
    def test_returns_none_when_no_cache(self, cache_file):
        assert mod.tt_cache_status_label() is None

    def test_returns_string_with_ticket_count(self, cache_file):
        mod.save_tt_raw_cache(TICKETS, EVENTS, ORDERS, CAP)
        label = mod.tt_cache_status_label()
        assert label is not None
        assert "2" in label
        assert "tickets" in label
        assert "ago" in label
