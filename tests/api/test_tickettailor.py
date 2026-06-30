import base64
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from ssg_dashboard.api.tickettailor import (
    _extract_records,
    _process_event_series,
    _process_tt_raw,
    _tt_to_iso,
    tt_fetch_all,
    tt_headers,
)


TICKETS_RAW = [
    {"id": "tkt1", "event_id": "evt1", "order_id": "ord1", "status": "ok"},
    {"id": "tkt2", "event_id": "evt2", "order_id": "ord2", "status": "ok"},
    {"id": "tkt3", "event_id": "evt1", "order_id": "ord_unknown", "status": "void"},
]

EVENTS_RAW = [
    {"id": "evt1", "name": "Show A", "start": 1704067200, "capacity": 100},
    {"id": "evt2", "name": "Show B", "start": 1704672000, "capacity": 80},
]

ORDERS_RAW = [
    {"id": "ord1", "txn_id": "PP001", "payment_method": {"type": "paypal"}, "refund_amount": 0},
    {"id": "ord2", "txn_id": "PP002", "payment_method": {"type": "stripe"}, "refund_amount": 500},
]


class TestTtHeaders:
    def test_authorization_is_basic_base64(self):
        headers = tt_headers("myapikey")
        expected = "Basic " + base64.b64encode(b"myapikey:").decode()
        assert headers["Authorization"] == expected

    def test_accept_is_json(self):
        assert tt_headers("k")["Accept"] == "application/json"


class TestExtractRecords:
    def test_list_input_returned_as_is(self):
        data = [{"a": 1}, {"b": 2}]
        assert _extract_records(data) == data

    def test_dict_with_data_key_returns_data_list(self):
        data = {"data": [{"a": 1}], "meta": {}}
        assert _extract_records(data) == [{"a": 1}]

    def test_dict_with_other_list_value_returns_first_list(self):
        data = {"records": [{"a": 1}], "count": 1}
        assert _extract_records(data) == [{"a": 1}]

    def test_unknown_structure_returns_empty_list(self):
        assert _extract_records("not a dict or list") == []
        assert _extract_records({"no_lists": "here"}) == []


class TestProcessTtRaw:
    def test_empty_inputs_return_empty_dataframes(self):
        tickets_df, events_df, capacity = _process_tt_raw([], [], [])
        assert tickets_df.empty
        assert events_df.empty
        assert capacity == {}

    def test_orders_join_adds_paypal_txn_id(self):
        tickets_df, _, _ = _process_tt_raw(TICKETS_RAW, EVENTS_RAW, ORDERS_RAW)
        assert "_paypal_txn_id" in tickets_df.columns
        row = tickets_df[tickets_df["id"] == "tkt1"].iloc[0]
        assert row["_paypal_txn_id"] == "PP001"

    def test_orders_join_adds_payment_type(self):
        tickets_df, _, _ = _process_tt_raw(TICKETS_RAW, EVENTS_RAW, ORDERS_RAW)
        row = tickets_df[tickets_df["id"] == "tkt2"].iloc[0]
        assert row["_order_payment_type"] == "stripe"

    def test_orders_join_adds_refund_amount(self):
        tickets_df, _, _ = _process_tt_raw(TICKETS_RAW, EVENTS_RAW, ORDERS_RAW)
        row = tickets_df[tickets_df["id"] == "tkt2"].iloc[0]
        assert row["_order_refund_amount"] == 500

    def test_unknown_order_id_fills_empty(self):
        tickets_df, _, _ = _process_tt_raw(TICKETS_RAW, EVENTS_RAW, ORDERS_RAW)
        row = tickets_df[tickets_df["id"] == "tkt3"].iloc[0]
        assert row["_paypal_txn_id"] == ""
        assert row["_order_payment_type"] == ""
        assert row["_order_refund_amount"] == 0

    def test_events_join_adds_event_name(self):
        tickets_df, _, _ = _process_tt_raw(TICKETS_RAW, EVENTS_RAW, ORDERS_RAW)
        assert "_event_name" in tickets_df.columns
        row = tickets_df[tickets_df["id"] == "tkt1"].iloc[0]
        assert row["_event_name"] == "Show A"

    def test_events_join_adds_performance_start(self):
        tickets_df, _, _ = _process_tt_raw(TICKETS_RAW, EVENTS_RAW, ORDERS_RAW)
        assert "_performance_start" in tickets_df.columns

    def test_capacity_extracted_from_events(self):
        _, _, capacity = _process_tt_raw(TICKETS_RAW, EVENTS_RAW, ORDERS_RAW)
        assert capacity == {"Show A": 100, "Show B": 80}

    def test_no_orders_returns_tickets_without_order_columns(self):
        tickets_df, _, _ = _process_tt_raw(TICKETS_RAW, EVENTS_RAW, [])
        assert "_paypal_txn_id" not in tickets_df.columns


class TestTtToIso:
    def test_unix_int_converted_to_iso(self):
        assert _tt_to_iso(1704067200) == "2024-01-01T00:00:00+00:00"

    def test_nested_dict_prefers_iso_field(self):
        value = {"date": "2024-01-01", "formatted": "Jan 1, 2024",
                 "iso": "2024-01-01T10:00:00+01:00", "time": "10:00:00",
                 "timezone": "+01:00", "unix": 1704099600}
        assert _tt_to_iso(value) == "2024-01-01T10:00:00+01:00"

    def test_nested_dict_falls_back_to_formatted_when_no_iso(self):
        assert _tt_to_iso({"formatted": "Jan 1, 2024", "unix": 1704067200}) == "Jan 1, 2024"

    def test_nested_dict_falls_back_to_date_when_no_iso_or_formatted(self):
        assert _tt_to_iso({"date": "2024-01-01", "unix": 1704067200}) == "2024-01-01"

    def test_nested_dict_falls_back_to_unix_as_last_resort(self):
        assert _tt_to_iso({"unix": 1704067200}) == "2024-01-01T00:00:00+00:00"

    def test_string_passed_through(self):
        assert _tt_to_iso("2024-01-01") == "2024-01-01"

    def test_none_and_empty_return_none(self):
        assert _tt_to_iso(None) is None
        assert _tt_to_iso("") is None


class TestProcessEventSeries:
    def test_extracts_sale_window_by_show_name(self):
        series = [{"id": "s1", "name": "Show A",
                   "tickets_available_at": {"date": "2024-01-01", "formatted": "Jan 1, 2024",
                                             "iso": "2024-01-01T00:00:00+00:00", "time": "00:00:00",
                                             "timezone": "+00:00", "unix": 1704067200},
                   "tickets_unavailable_at": {"date": "2024-02-01", "formatted": "Feb 1, 2024",
                                               "iso": "2024-02-01T00:00:00+00:00", "time": "00:00:00",
                                               "timezone": "+00:00", "unix": 1706745600}}]
        result = _process_event_series(series)
        assert result == {"Show A": {
            "tickets_available_at": "2024-01-01T00:00:00+00:00",
            "tickets_unavailable_at": "2024-02-01T00:00:00+00:00",
        }}

    def test_series_without_name_skipped(self):
        assert _process_event_series([{"id": "s1", "tickets_available_at": 1}]) == {}

    def test_series_without_dates_skipped(self):
        assert _process_event_series([{"id": "s1", "name": "Show A"}]) == {}

    def test_empty_input_returns_empty_dict(self):
        assert _process_event_series([]) == {}


def _resp(status_code=200, json_data=None, text=""):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data if json_data is not None else {}
    r.text = text
    return r


class TestTtFetchAll:
    @patch("ssg_dashboard.api.tickettailor.requests.get")
    def test_single_page_returns_all_records(self, mock_get):
        records = [{"id": f"e{i}"} for i in range(5)]
        mock_get.return_value = _resp(json_data={"data": records})

        result = tt_fetch_all("key", "events")

        assert result == records
        assert mock_get.call_count == 1

    @patch("ssg_dashboard.api.tickettailor.requests.get")
    def test_paginates_using_starting_after_cursor(self, mock_get):
        page1 = [{"id": f"e{i}"} for i in range(100)]
        page2 = [{"id": "e100"}]
        mock_get.side_effect = [
            _resp(json_data={"data": page1}),
            _resp(json_data={"data": page2}),
        ]

        result = tt_fetch_all("key", "events")

        assert len(result) == 101
        assert mock_get.call_count == 2
        second_call_params = mock_get.call_args_list[1].kwargs["params"]
        assert second_call_params["starting_after"] == "e99"

    @patch("ssg_dashboard.api.tickettailor.requests.get")
    def test_stops_when_page_smaller_than_limit(self, mock_get):
        page1 = [{"id": "e1"}, {"id": "e2"}]
        mock_get.return_value = _resp(json_data={"data": page1})

        result = tt_fetch_all("key", "events")

        assert result == page1
        assert mock_get.call_count == 1

    @patch("ssg_dashboard.api.tickettailor.requests.get")
    def test_stops_when_last_record_has_no_id(self, mock_get):
        full_page = [{"name": f"e{i}"} for i in range(100)]  # no "id" key — cursor unavailable
        mock_get.return_value = _resp(json_data={"data": full_page})

        result = tt_fetch_all("key", "events")

        assert result == full_page
        assert mock_get.call_count == 1

    @patch("ssg_dashboard.api.tickettailor.requests.get")
    def test_non_200_raises_runtime_error(self, mock_get):
        mock_get.return_value = _resp(status_code=401, text="Unauthorized")

        with pytest.raises(RuntimeError, match="401"):
            tt_fetch_all("key", "events")

    @patch("ssg_dashboard.api.tickettailor.requests.get")
    def test_respects_max_pages_limit(self, mock_get):
        full_page = [{"id": f"e{i}"} for i in range(100)]
        mock_get.return_value = _resp(json_data={"data": full_page})

        result = tt_fetch_all("key", "events", max_pages=3)

        assert mock_get.call_count == 3
        assert len(result) == 300

    @patch("ssg_dashboard.api.tickettailor.requests.get")
    def test_extracts_records_from_plain_list_response(self, mock_get):
        records = [{"id": "e1"}, {"id": "e2"}]
        mock_get.return_value = _resp(json_data=records)

        result = tt_fetch_all("key", "events")

        assert result == records
