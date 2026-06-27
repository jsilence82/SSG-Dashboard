import pytest

import ssg_dashboard.persistence.tt_cache as mod


@pytest.fixture
def cache_file(tmp_path, monkeypatch):
    path = tmp_path / "tt_raw_cache.json"
    monkeypatch.setattr(mod, "TT_RAW_CACHE_FILE", path)
    return path


TICKETS = [{"id": "t1", "event_id": "e1"}, {"id": "t2", "event_id": "e2"}]
EVENTS  = [{"id": "e1", "name": "Show A"}, {"id": "e2", "name": "Show B"}]
ORDERS  = [{"id": "o1", "txn_id": "PP1"}]
CAP     = {"Show A": 100, "Show B": 80}


class TestSaveLoadRoundtrip:
    def test_all_fields_preserved(self, cache_file):
        mod.save_tt_raw_cache(TICKETS, EVENTS, ORDERS, CAP)
        result = mod.load_tt_raw_cache()
        assert result is not None
        tickets, events, orders, capacity, saved_at = result
        assert tickets == TICKETS
        assert events == EVENTS
        assert orders == ORDERS
        assert capacity == CAP
        assert saved_at != ""

    def test_empty_lists_preserved(self, cache_file):
        mod.save_tt_raw_cache([], [], [], {})
        tickets, events, orders, capacity, _ = mod.load_tt_raw_cache()
        assert tickets == []
        assert events == []
        assert orders == []
        assert capacity == {}


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
