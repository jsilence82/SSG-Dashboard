import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from ssg_dashboard.api.paypal import pp_fetch_transactions, pp_get_token


def _mock_response(data, status_code=200):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = data
    r.text = json.dumps(data)
    r.raise_for_status = MagicMock()
    return r


def _txn_payload(txn_id="T1", gross="10.00", fee="-0.30", ref_id="", pages=1):
    return {
        "transaction_details": [{
            "transaction_info": {
                "transaction_id":             txn_id,
                "transaction_initiation_date": "2024-01-15T10:00:00+00:00",
                "transaction_amount":          {"value": gross},
                "fee_amount":                  {"value": fee},
                "transaction_subject":         "Test ticket",
                "invoice_id":                  "INV1",
                "transaction_status":          "S",
                "paypal_reference_id":         ref_id,
            }
        }],
        "total_pages": pages,
    }


class TestPpGetToken:
    @patch("ssg_dashboard.api.paypal.requests.post")
    def test_success_returns_token(self, mock_post):
        mock_post.return_value = _mock_response({"access_token": "tok_abc"}, 200)
        ok, result = pp_get_token("cid", "secret")
        assert ok is True
        assert result == "tok_abc"

    @patch("ssg_dashboard.api.paypal.requests.post")
    def test_http_failure_returns_false(self, mock_post):
        mock_post.return_value = _mock_response({}, 401)
        ok, result = pp_get_token("cid", "secret")
        assert ok is False
        assert "401" in result

    @patch("ssg_dashboard.api.paypal.requests.post")
    def test_network_error_returns_false(self, mock_post):
        import requests as req_lib
        mock_post.side_effect = req_lib.RequestException("timeout")
        ok, result = pp_get_token("cid", "secret")
        assert ok is False
        assert "timeout" in result

    @patch("ssg_dashboard.api.paypal.requests.post")
    def test_strips_whitespace_from_credentials(self, mock_post):
        mock_post.return_value = _mock_response({"access_token": "tok"}, 200)
        pp_get_token("  cid  ", "  secret  ")
        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["auth"] == ("cid", "secret")

    @patch("ssg_dashboard.api.paypal.requests.post")
    def test_sandbox_uses_sandbox_url(self, mock_post):
        mock_post.return_value = _mock_response({"access_token": "tok"}, 200)
        pp_get_token("cid", "secret", sandbox=True)
        url = mock_post.call_args.args[0]
        assert "sandbox" in url


class TestPpFetchTransactions:
    @patch("ssg_dashboard.api.paypal.requests.get")
    def test_parses_transaction_fields(self, mock_get):
        mock_get.return_value = _mock_response(_txn_payload("TX1", "15.00", "-0.50"))
        results = pp_fetch_transactions("tok", datetime(2024, 1, 1), datetime(2024, 1, 31))
        assert len(results) == 1
        t = results[0]
        assert t["txn_id"] == "TX1"
        assert t["date"] == "2024-01-15"
        assert t["gross"] == pytest.approx(15.0)
        assert t["fee"] == pytest.approx(-0.5)
        assert t["net"] == pytest.approx(14.5)

    @patch("ssg_dashboard.api.paypal.requests.get")
    def test_refund_transaction_carries_reference_id(self, mock_get):
        mock_get.return_value = _mock_response(_txn_payload("REF1", "-15.00", "0.50", ref_id="TX1"))
        results = pp_fetch_transactions("tok", datetime(2024, 1, 1), datetime(2024, 1, 31))
        assert results[0]["paypal_reference_id"] == "TX1"

    @patch("ssg_dashboard.api.paypal.requests.get")
    def test_chunks_into_31_day_windows(self, mock_get):
        mock_get.return_value = _mock_response({"transaction_details": [], "total_pages": 1})
        # 2024-01-01 to 2024-03-15 spans 3 windows (31 + 31 + remaining)
        pp_fetch_transactions("tok", datetime(2024, 1, 1), datetime(2024, 3, 15))
        assert mock_get.call_count == 3

    @patch("ssg_dashboard.api.paypal.requests.get")
    def test_paginates_until_last_page(self, mock_get):
        page1 = _mock_response(_txn_payload("T1", pages=2))
        page2 = _mock_response(_txn_payload("T2", pages=2))
        mock_get.side_effect = [_mock_response(page1.json.return_value),
                                _mock_response(page2.json.return_value)]
        results = pp_fetch_transactions("tok", datetime(2024, 1, 1), datetime(2024, 1, 31))
        assert len(results) == 2
        assert mock_get.call_count == 2

    @patch("ssg_dashboard.api.paypal.requests.get")
    def test_401_authentication_failure_raises_permission_error(self, mock_get):
        r = MagicMock()
        r.status_code = 401
        r.json.return_value = {"name": "AUTHENTICATION_FAILURE"}
        r.text = '{"name": "AUTHENTICATION_FAILURE"}'
        mock_get.return_value = r
        with pytest.raises(PermissionError, match="Transaction Search"):
            pp_fetch_transactions("tok", datetime(2024, 1, 1), datetime(2024, 1, 31))

    @patch("ssg_dashboard.api.paypal.requests.get")
    def test_401_generic_raises_permission_error(self, mock_get):
        r = MagicMock()
        r.status_code = 401
        r.json.return_value = {"name": "OTHER_ERROR"}
        r.text = "Unauthorized"
        mock_get.return_value = r
        with pytest.raises(PermissionError, match="PayPal 401"):
            pp_fetch_transactions("tok", datetime(2024, 1, 1), datetime(2024, 1, 31))
