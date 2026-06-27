from datetime import date

import pandas as pd
import pytest

from ssg_dashboard.mapping import _parse_date_column, build_canonical, guess_column


class TestGuessColumn:
    def test_finds_exact_keyword_match(self):
        assert guess_column(["show", "price"], ["show"]) == "show"

    def test_finds_partial_keyword_match(self):
        assert guess_column(["event_name", "ticket_type"], ["event"]) == "event_name"

    def test_case_insensitive(self):
        assert guess_column(["ShowName", "TicketType"], ["show"]) == "ShowName"

    def test_first_keyword_wins(self):
        cols = ["title", "event_name"]
        result = guess_column(cols, ["title", "event"])
        assert result == "title"

    def test_returns_none_when_no_match(self):
        assert guess_column(["price", "qty"], ["email", "show"]) is None

    def test_empty_columns(self):
        assert guess_column([], ["show"]) is None


class TestParseDateColumn:
    def test_numeric_dtype_treated_as_unix(self):
        col = pd.Series([1704067200, 1704153600], dtype="int64")
        result = _parse_date_column(col)
        assert result.dt.date.iloc[0] == date(2024, 1, 1)
        assert result.dt.date.iloc[1] == date(2024, 1, 2)

    def test_mostly_numeric_strings_treated_as_unix(self):
        col = pd.Series(["1704067200", "1704153600"])
        result = _parse_date_column(col)
        assert result.dt.year.iloc[0] == 2024

    def test_iso_string_dates_parsed_correctly(self):
        col = pd.Series(["2024-03-15", "2024-06-01"])
        result = _parse_date_column(col)
        assert result.dt.date.iloc[0] == date(2024, 3, 15)
        assert result.dt.date.iloc[1] == date(2024, 6, 1)

    def test_mixed_unparseable_becomes_nat(self):
        col = pd.Series(["not-a-date", "also-not"])
        result = _parse_date_column(col)
        assert result.isna().all()


class TestBuildCanonical:
    def test_required_fields_present(self, sample_raw_df, base_mapping):
        out = build_canonical(sample_raw_df, base_mapping, prices_in_cents=False, revenue_is_per_unit=False)
        assert list(out["show"]) == ["Show A", "Show A", "Show B"]
        assert list(out["category"]) == ["Adult", "Child", "Adult"]

    def test_quantity_defaults_to_1_when_not_mapped(self, sample_raw_df, base_mapping):
        mapping = {**base_mapping, "quantity": None}
        out = build_canonical(sample_raw_df, mapping, prices_in_cents=False, revenue_is_per_unit=False)
        assert (out["quantity"] == 1).all()

    def test_revenue_defaults_to_zero_when_not_mapped(self, sample_raw_df, base_mapping):
        mapping = {**base_mapping, "revenue": None}
        out = build_canonical(sample_raw_df, mapping, prices_in_cents=False, revenue_is_per_unit=False)
        assert (out["revenue"] == 0).all()

    def test_prices_in_cents_divides_by_100(self, sample_raw_df, base_mapping):
        out = build_canonical(sample_raw_df, base_mapping, prices_in_cents=True, revenue_is_per_unit=False)
        assert out["revenue"].iloc[0] == pytest.approx(28.0)
        assert out["revenue"].iloc[1] == pytest.approx(7.0)

    def test_revenue_is_per_unit_multiplies_by_quantity(self, sample_raw_df, base_mapping):
        out = build_canonical(sample_raw_df, base_mapping, prices_in_cents=True, revenue_is_per_unit=True)
        assert out["revenue"].iloc[0] == pytest.approx(56.0)   # 28.0 * 2
        assert out["revenue"].iloc[1] == pytest.approx(7.0)    # 7.0  * 1

    def test_status_defaults_to_unknown_when_not_mapped(self, sample_raw_df, base_mapping):
        mapping = {**base_mapping, "status": None}
        out = build_canonical(sample_raw_df, mapping, prices_in_cents=False, revenue_is_per_unit=False)
        assert (out["status"] == "unknown").all()

    def test_buyer_id_prefers_email(self, sample_raw_df, base_mapping):
        out = build_canonical(sample_raw_df, base_mapping, prices_in_cents=False, revenue_is_per_unit=False)
        assert out["buyer_id"].iloc[0] == "a@example.com"

    def test_buyer_id_falls_back_to_name_when_email_empty(self, sample_raw_df, base_mapping):
        df = sample_raw_df.copy()
        df["buyer_email"] = ""
        out = build_canonical(df, base_mapping, prices_in_cents=False, revenue_is_per_unit=False)
        assert out["buyer_id"].iloc[0] == "alice"

    def test_paypal_txn_id_auto_detected_from_underscore_column(self, sample_raw_df, base_mapping):
        out = build_canonical(sample_raw_df, base_mapping, prices_in_cents=False, revenue_is_per_unit=False)
        assert out["paypal_txn_id"].iloc[0] == "PP001"
        assert out["paypal_txn_id"].iloc[2] == "PP002"

    def test_paypal_txn_id_uses_explicit_mapping_over_auto(self, sample_raw_df, base_mapping):
        df = sample_raw_df.copy()
        df["explicit_txn"] = ["EX001", "EX002", "EX003"]
        mapping = {**base_mapping, "paypal_txn_id": "explicit_txn"}
        out = build_canonical(df, mapping, prices_in_cents=False, revenue_is_per_unit=False)
        assert out["paypal_txn_id"].iloc[0] == "EX001"

    def test_occurrence_falls_back_to_event_id(self, sample_raw_df, base_mapping):
        out = build_canonical(sample_raw_df, base_mapping, prices_in_cents=False, revenue_is_per_unit=False)
        assert list(out["occurrence"]) == ["evt1", "evt1", "evt2"]

    def test_order_payment_metadata_carried_through(self, sample_raw_df, base_mapping):
        out = build_canonical(sample_raw_df, base_mapping, prices_in_cents=False, revenue_is_per_unit=False)
        assert (out["_order_payment_type"] == "paypal").all()
        assert (out["_order_refund_amount"] == 0).all()

    def test_email_lowercased_and_stripped(self, sample_raw_df, base_mapping):
        df = sample_raw_df.copy()
        df["buyer_email"] = ["  A@EXAMPLE.COM  ", "B@Example.com", "c@example.com"]
        out = build_canonical(df, base_mapping, prices_in_cents=False, revenue_is_per_unit=False)
        assert out["email"].iloc[0] == "a@example.com"
        assert out["email"].iloc[1] == "b@example.com"
