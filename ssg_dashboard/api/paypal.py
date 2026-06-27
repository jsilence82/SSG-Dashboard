"""PayPal Reporting API client."""

from datetime import datetime, timedelta

import requests

from ..config import PP_BASE_URL


def pp_get_token(client_id: str, secret: str, sandbox: bool = False) -> tuple[bool, str]:
    client_id = client_id.strip()
    secret    = secret.strip()
    base = "https://api.sandbox.paypal.com" if sandbox else PP_BASE_URL
    try:
        r = requests.post(
            f"{base}/v1/oauth2/token",
            auth=(client_id, secret),
            data={
                "grant_type": "client_credentials",
                "scope": "https://uri.paypal.com/services/reporting/search/read",
            },
            timeout=20,
        )
        if r.status_code == 200:
            return True, r.json()["access_token"]
        return False, f"HTTP {r.status_code}: {r.text[:300]}"
    except requests.RequestException as exc:
        return False, str(exc)


def pp_fetch_transactions(
    access_token: str,
    start_date: datetime,
    end_date: datetime,
    sandbox: bool = False,
) -> list[dict]:
    # PayPal Transaction Search API requires chunks of ≤31 days.
    access_token = access_token.strip()
    base = "https://api.sandbox.paypal.com" if sandbox else PP_BASE_URL
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    results = []
    cursor = start_date
    while cursor < end_date:
        window_end = min(cursor + timedelta(days=31), end_date)
        page = 1
        while True:
            params = {
                "start_date":                    cursor.strftime("%Y-%m-%dT00:00:00+00:00"),
                "end_date":                      window_end.strftime("%Y-%m-%dT23:59:59+00:00"),
                "fields":                        "transaction_info",
                "page_size":                     500,
                "page":                          page,
                "balance_affecting_records_only": "Y",
            }
            r = requests.get(
                f"{base}/v1/reporting/transactions",
                headers=headers,
                params=params,
                timeout=30,
            )
            if r.status_code == 401:
                try:
                    name = r.json().get("name", "")
                except Exception:
                    name = ""
                if name == "AUTHENTICATION_FAILURE":
                    raise PermissionError(
                        "PayPal returned AUTHENTICATION_FAILURE on the Transaction Search endpoint. "
                        "Your REST API app likely does not have the Transaction Search feature enabled. "
                        "Fix: go to developer.paypal.com → My Apps → select your app → "
                        "enable 'Transaction Search' under the Live (or Sandbox) features, then save."
                    )
                raise PermissionError(f"PayPal 401: {r.text[:300]}")
            r.raise_for_status()
            data = r.json()
            for item in data.get("transaction_details", []):
                ti = item.get("transaction_info", {})
                gross = float((ti.get("transaction_amount") or {}).get("value", 0))
                fee   = float((ti.get("fee_amount")         or {}).get("value", 0))
                results.append({
                    "txn_id":               ti.get("transaction_id", ""),
                    "date":                 (ti.get("transaction_initiation_date") or "")[:10],
                    "gross":                gross,
                    "fee":                  fee,
                    "net":                  gross + fee,
                    "subject":              ti.get("transaction_subject", ""),
                    "invoice_id":           ti.get("invoice_id", ""),
                    "status":               ti.get("transaction_status", ""),
                    # On refund/reversal transactions PayPal sets this to the original txn_id
                    "paypal_reference_id":  ti.get("paypal_reference_id", ""),
                })
            if page >= data.get("total_pages", 1):
                break
            page += 1
        cursor = window_end + timedelta(days=1)
    return results
