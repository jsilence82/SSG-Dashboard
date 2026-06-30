from datetime import datetime

import pandas as pd
import pytest

from ssg_dashboard.sections.reconciliation import (
    _active,
    _filter_paypal_for_show,
    _parse_tt_date,
    _paypal_ids_for_show,
    _paypal_only,
    build_reconciliation,
)


def _txn(txn_id, gross, fee, paypal_reference_id=""):
    return {
        "txn_id": txn_id,
        "gross": gross,
        "fee": fee,
        "net": gross + fee,
        "paypal_reference_id": paypal_reference_id,
    }


def _show_df(rows):
    return pd.DataFrame(rows)


def _sample_df():
    """Two nights for one show, all tickets active and paid via PayPal (no txn linkage yet)."""
    return pd.DataFrame({
        "show":                 ["Carmilla", "Carmilla", "Carmilla"],
        "status":               ["complete", "complete", "complete"],
        "performance_date":     pd.to_datetime(
            ["2024-01-05", "2024-01-05", "2024-01-12"], utc=True),
        "revenue":              [20.0, 15.0, 30.0],
        "quantity":             [1, 1, 2],
        "category":             ["Adult", "Child", "Adult"],
        "paypal_txn_id":        ["", "", ""],
        "_order_payment_type":  ["paypal", "paypal", "paypal"],
        "_order_refund_amount": [0, 0, 0],
    })


class TestActive:
    def test_drops_voided_refunded_and_cancelled_rows(self):
        df = pd.DataFrame({"status": ["complete", "void", "voided", "refund",
                                       "refunded", "cancelled", "canceled"]})
        result = _active(df)
        assert list(result["status"]) == ["complete"]

    def test_case_insensitive(self):
        df = pd.DataFrame({"status": ["VOID", "Complete"]})
        assert list(_active(df)["status"]) == ["Complete"]

    def test_no_status_column_returns_unchanged(self):
        df = pd.DataFrame({"show": ["A", "B"]})
        assert len(_active(df)) == 2

    def test_missing_status_values_kept(self):
        df = pd.DataFrame({"status": [None, "complete"]})
        assert len(_active(df)) == 2


class TestPaypalOnly:
    def test_keeps_paypal_rows_only(self):
        df = _show_df([
            {"_order_payment_type": "paypal"},
            {"_order_payment_type": "stripe"},
            {"_order_payment_type": "cash"},
        ])
        result = _paypal_only(df)
        assert len(result) == 1
        assert result.iloc[0]["_order_payment_type"] == "paypal"

    def test_case_insensitive(self):
        df = _show_df([{"_order_payment_type": "PayPal"}, {"_order_payment_type": "Stripe"}])
        assert len(_paypal_only(df)) == 1

    def test_missing_or_blank_payment_type_excluded(self):
        df = _show_df([{"_order_payment_type": ""}, {"_order_payment_type": None}])
        assert _paypal_only(df).empty

    def test_missing_column_returns_empty(self):
        df = pd.DataFrame({"show": ["A", "B"]})
        assert _paypal_only(df).empty


class TestParseTtDate:
    def test_none_returns_none(self):
        assert _parse_tt_date(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_tt_date("") is None

    def test_valid_iso_string_parsed(self):
        assert _parse_tt_date("2024-01-01T10:00:00+00:00") == \
            datetime.fromisoformat("2024-01-01T10:00:00+00:00")

    def test_invalid_string_returns_none(self):
        assert _parse_tt_date("not-a-date") is None


class TestPaypalIdsForShow:
    def test_no_paypal_txn_id_column_returns_empty_set(self):
        df = pd.DataFrame({"status": ["complete"]})
        assert _paypal_ids_for_show(df) == set()

    def test_active_tickets_included(self):
        df = _show_df([
            {"status": "complete", "paypal_txn_id": "PP1", "_order_payment_type": "paypal",
             "_order_refund_amount": 0},
            {"status": "complete", "paypal_txn_id": "PP2", "_order_payment_type": "paypal",
             "_order_refund_amount": 0},
        ])
        assert _paypal_ids_for_show(df) == {"PP1", "PP2"}

    def test_blank_and_nan_ids_excluded(self):
        df = _show_df([
            {"status": "complete", "paypal_txn_id": "", "_order_payment_type": "paypal",
             "_order_refund_amount": 0},
            {"status": "complete", "paypal_txn_id": None, "_order_payment_type": "paypal",
             "_order_refund_amount": 0},
        ])
        assert _paypal_ids_for_show(df) == set()

    def test_active_ticket_paid_by_other_method_excluded(self):
        df = _show_df([{"status": "complete", "paypal_txn_id": "PP1",
                         "_order_payment_type": "stripe", "_order_refund_amount": 0}])
        assert _paypal_ids_for_show(df) == set()

    def test_voided_transferred_ticket_included(self):
        df = _show_df([{"status": "void", "paypal_txn_id": "PP1",
                         "_order_payment_type": "paypal", "_order_refund_amount": 0}])
        assert _paypal_ids_for_show(df) == {"PP1"}

    def test_voided_refunded_ticket_excluded(self):
        df = _show_df([{"status": "void", "paypal_txn_id": "PP1",
                         "_order_payment_type": "paypal", "_order_refund_amount": 10}])
        assert _paypal_ids_for_show(df) == set()

    def test_voided_non_paypal_ticket_excluded(self):
        df = _show_df([{"status": "void", "paypal_txn_id": "PP1",
                         "_order_payment_type": "stripe", "_order_refund_amount": 0}])
        assert _paypal_ids_for_show(df) == set()


class TestFilterPaypalForShow:
    def test_empty_paypal_txns_returns_empty(self):
        df = _show_df([{"status": "complete", "paypal_txn_id": "PP1"}])
        assert _filter_paypal_for_show(df, []) == []

    def test_no_mapped_ids_returns_all_as_fallback(self):
        df = pd.DataFrame({"status": ["complete"]})  # no paypal_txn_id column at all
        txns = [_txn("PP1", 10, -1)]
        assert _filter_paypal_for_show(df, txns) == txns

    def test_filters_to_matching_txn_id_only(self):
        df = _show_df([{"status": "complete", "paypal_txn_id": "PP1",
                         "_order_payment_type": "paypal", "_order_refund_amount": 0}])
        txns = [_txn("PP1", 10, -1), _txn("PP2", 20, -2)]
        result = _filter_paypal_for_show(df, txns)
        assert [t["txn_id"] for t in result] == ["PP1"]

    def test_includes_refund_via_reference_id(self):
        df = _show_df([{"status": "complete", "paypal_txn_id": "PP1",
                         "_order_payment_type": "paypal", "_order_refund_amount": 0}])
        refund = _txn("R1", -10, 0, paypal_reference_id="PP1")
        txns = [_txn("PP1", 10, -1), refund]
        result = _filter_paypal_for_show(df, txns)
        assert {t["txn_id"] for t in result} == {"PP1", "R1"}


class TestBuildReconciliationTotalsFromTtRevenue:
    """When no PayPal transactions are matched, totals fall back to TT revenue/quantity."""

    def test_per_night_totals_use_tt_revenue(self):
        totals_df, *_ = build_reconciliation(_sample_df(), [])
        body = totals_df.drop(index="TOTAL")
        assert len(body) == 2
        night1 = body.iloc[0]
        assert night1["Gross (€)"] == 35.0
        assert night1["Fees (€)"] == 0.0
        assert night1["Net (€)"] == 35.0
        assert night1["Transactions"] == 2  # quantity sum, not txn count

    def test_total_row_sums_all_nights(self):
        totals_df, *_ = build_reconciliation(_sample_df(), [])
        total = totals_df.loc["TOTAL"]
        assert total["Gross (€)"] == 65.0
        assert total["Transactions"] == 4

    def test_missing_performance_date_column_returns_empty_totals(self):
        df = pd.DataFrame({"show": ["Carmilla"], "status": ["complete"],
                            "revenue": [20.0], "quantity": [1], "category": ["Adult"]})
        totals_df, stats_df, unmatched_df, show_txns = build_reconciliation(df, [])
        assert totals_df.empty
        assert list(totals_df.columns) == \
            ["Performance Date", "Transactions", "Gross (€)", "Fees (€)", "Net (€)"]
        assert stats_df.empty


class TestBuildReconciliationTotalsFromPaypal:
    def test_matched_paypal_totals_override_tt_revenue(self):
        df = _sample_df()
        df["paypal_txn_id"] = ["PP1", "PP2", ""]
        txns = [_txn("PP1", 20.0, -1.0), _txn("PP2", 15.0, -0.8)]

        totals_df, *_ = build_reconciliation(df, txns)
        night1 = totals_df.drop(index="TOTAL").iloc[0]

        assert night1["Gross (€)"] == 35.0
        assert night1["Fees (€)"] == -1.8
        assert night1["Net (€)"] == pytest.approx(33.2)
        assert night1["Transactions"] == 2  # txn count this time, matches ticket count here


class TestBuildReconciliationTransferredVoided:
    """Voided-but-transferred tickets: original PayPal charge still valid, no refund issued.
    They must count toward PayPal gross/fees/net but not toward ticket counts."""

    def test_voided_transfer_counted_in_totals_but_not_ticket_stats(self):
        df = pd.DataFrame({
            "show":                 ["Carmilla", "Carmilla"],
            "status":               ["complete", "void"],
            "performance_date":     pd.to_datetime(["2024-01-05", "2024-01-05"], utc=True),
            "revenue":              [20.0, 20.0],
            "quantity":             [1, 1],
            "category":             ["Adult", "Adult"],
            "paypal_txn_id":        ["PP1", "PP2"],
            "_order_payment_type":  ["paypal", "paypal"],
            "_order_refund_amount": [0, 0],
        })
        txns = [_txn("PP1", 20.0, -1.0), _txn("PP2", 20.0, -1.0)]

        totals_df, stats_df, unmatched_df, show_txns = build_reconciliation(df, txns)

        night1 = totals_df.drop(index="TOTAL").iloc[0]
        assert night1["Gross (€)"] == 40.0
        assert night1["Fees (€)"] == -2.0
        assert night1["Net (€)"] == 38.0
        assert night1["Transactions"] == 2  # both PayPal charges, not ticket quantity

        stats_night1 = stats_df.drop(index="TOTAL").iloc[0]
        assert stats_night1["Total Tickets"] == 1  # only the active ticket

    def test_voided_refunded_ticket_excluded_entirely(self):
        df = pd.DataFrame({
            "show":                 ["Carmilla"],
            "status":               ["void"],
            "performance_date":     pd.to_datetime(["2024-01-05"], utc=True),
            "revenue":              [20.0],
            "quantity":             [1],
            "category":             ["Adult"],
            "paypal_txn_id":        ["PP1"],
            "_order_payment_type":  ["paypal"],
            "_order_refund_amount": [20.0],
        })
        totals_df, stats_df, *_ = build_reconciliation(df, [_txn("PP1", 20.0, -1.0)])
        assert totals_df.empty
        assert stats_df.empty


class TestBuildReconciliationTotalPaid:
    def test_operator_with_real_payment_included_in_gross(self):
        """Operator-tagged tickets that were genuinely paid (total_paid > 0) must
        contribute to Gross — they represent real money collected at the box office."""
        df = pd.DataFrame({
            "show":                 ["Tartuffe"] * 4,
            "status":               ["valid"] * 4,
            "performance_date":     pd.to_datetime(["2025-05-09"] * 4, utc=True),
            "revenue":              [22.0, 22.0, 13.0, 13.0],
            "quantity":             [1, 1, 1, 1],
            "category":             ["Adult"] * 4,
            "paypal_txn_id":        ["PP1", "PP2", "", ""],
            "_order_payment_type":  ["paypal", "paypal", "operator", "operator"],
            "_order_refund_amount": [0, 0, 0, 0],
            "_order_total_paid":    [22.0, 22.0, 13.0, 13.0],  # operator order was fully paid
        })

        totals_df, *_ = build_reconciliation(df, [])

        total = totals_df.loc["TOTAL"]
        assert total["Gross (€)"] == 70.0   # all 4 tickets — operator fully paid, included
        assert total["Transactions"] == 4

    def test_transferred_order_contributes_zero_gross(self):
        """When total_paid=0 (order transferred elsewhere, nothing actually retained),
        those tickets appear in ticket counts but contribute €0 to gross."""
        df = pd.DataFrame({
            "show":                 ["Carmilla"] * 3,
            "status":               ["complete"] * 3,
            "performance_date":     pd.to_datetime(["2024-01-05"] * 3, utc=True),
            "revenue":              [20.0, 13.0, 13.0],
            "quantity":             [1, 1, 1],
            "category":             ["Adult"] * 3,
            "paypal_txn_id":        ["PP1", "", ""],
            "_order_payment_type":  ["paypal", "no_cost", "no_cost"],
            "_order_refund_amount": [0, 0, 0],
            "_order_total_paid":    [20.0, 0.0, 0.0],  # no_cost order: total_paid=0 (transferred)
        })

        totals_df, stats_df, *_ = build_reconciliation(df, [])

        night = totals_df.drop(index="TOTAL").iloc[0]
        assert night["Gross (€)"] == 20.0       # only the paypal ticket's total_paid
        assert night["Transactions"] == 3        # all 3 tickets still counted

        stats = stats_df.drop(index="TOTAL").iloc[0]
        assert stats["Total Tickets"] == 3       # ticket counts unaffected

    def test_mixed_real_tartuffe_scenario(self):
        """Mirrors the real Tartuffe data: paypal=3563, operator fully paid=26,
        no_cost transferred=26 (total_paid=0). tt_gross should equal 3589."""
        n = 293  # paypal tickets
        df_paypal = pd.DataFrame({
            "show":                ["Tartuffe"] * n,
            "status":              ["valid"] * n,
            "performance_date":    pd.to_datetime(["2025-05-09"] * n, utc=True),
            "revenue":             [3563.0 / n] * n,
            "quantity":            [1] * n,
            "category":            ["Adult"] * n,
            "paypal_txn_id":       ["PP"] * n,
            "_order_payment_type": ["paypal"] * n,
            "_order_refund_amount":[0] * n,
            "_order_total_paid":   [3563.0 / n] * n,
        })
        df_operator = pd.DataFrame({
            "show":                ["Tartuffe"] * 2,
            "status":              ["valid"] * 2,
            "performance_date":    pd.to_datetime(["2025-05-09"] * 2, utc=True),
            "revenue":             [13.0, 13.0],
            "quantity":            [1, 1],
            "category":            ["Adult"] * 2,
            "paypal_txn_id":       ["", ""],
            "_order_payment_type": ["operator"] * 2,
            "_order_refund_amount":[0, 0],
            "_order_total_paid":   [13.0, 13.0],  # fully paid
        })
        df_nocost = pd.DataFrame({
            "show":                ["Tartuffe"] * 10,
            "status":              ["valid"] * 10,
            "performance_date":    pd.to_datetime(["2025-05-09"] * 10, utc=True),
            "revenue":             [2.6] * 10,
            "quantity":            [1] * 10,
            "category":            ["Adult"] * 10,
            "paypal_txn_id":       [""] * 10,
            "_order_payment_type": ["no_cost"] * 10,
            "_order_refund_amount":[0] * 10,
            "_order_total_paid":   [0.0] * 10,  # transferred — nothing actually paid
        })
        df = pd.concat([df_paypal, df_operator, df_nocost], ignore_index=True)
        totals_df, *_ = build_reconciliation(df, [])
        assert totals_df.loc["TOTAL"]["Gross (€)"] == pytest.approx(3589.0, rel=1e-3)


class TestBuildReconciliationShowFilter:
    def test_show_filter_excludes_other_shows(self):
        carmilla = _sample_df()
        medea = _sample_df().assign(show="Medea", revenue=[100.0, 100.0, 100.0])
        combined = pd.concat([carmilla, medea], ignore_index=True)

        totals_df, *_ = build_reconciliation(combined, [], show_filter="Carmilla")

        assert totals_df.loc["TOTAL"]["Gross (€)"] == 65.0


class TestBuildReconciliationStatistics:
    def test_category_breakdown_per_night(self):
        _, stats_df, _, _ = build_reconciliation(_sample_df(), [])
        night1 = stats_df.drop(index="TOTAL").iloc[0]
        assert night1["Adult"] == 1
        assert night1["Child"] == 1
        assert night1["Total Tickets"] == 2

    def test_total_row_sums_categories(self):
        _, stats_df, _, _ = build_reconciliation(_sample_df(), [])
        total = stats_df.loc["TOTAL"]
        assert total["Total Tickets"] == 4
        assert total["Adult"] == 3
        assert total["Child"] == 1


class TestBuildReconciliationUnmatched:
    def test_all_paypal_txns_unmatched_when_no_tt_mapping_exists(self):
        txns = [_txn("PP1", 20.0, -1.0), _txn("PP2", 99.0, -5.0)]
        totals_df, stats_df, unmatched_df, show_txns = build_reconciliation(_sample_df(), txns)

        assert len(show_txns) == 2  # fallback: nothing mapped yet, all returned
        assert set(unmatched_df["txn_id"]) == {"PP1", "PP2"}

    def test_matched_refund_not_flagged_unmatched(self):
        df = _sample_df()
        df["paypal_txn_id"] = ["PP1", "", ""]
        refund = _txn("R1", -20.0, 0.0, paypal_reference_id="PP1")
        txns = [_txn("PP1", 20.0, -1.0), refund]

        totals_df, stats_df, unmatched_df, show_txns = build_reconciliation(df, txns)

        assert unmatched_df.empty
        assert {t["txn_id"] for t in show_txns} == {"PP1", "R1"}
