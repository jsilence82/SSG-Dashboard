import base64

import pandas as pd
import pytest

from ssg_dashboard.api.tickettailor import _extract_records, _process_tt_raw, tt_headers


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
