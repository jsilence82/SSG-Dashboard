"""Reconciliation report: Totals + Statistics tables cross-referenced with PayPal."""

from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from ..api.paypal import pp_get_token
from ..persistence.paypal_cache import (
    _in_range,
    cache_status_label,
    clear_paypal_cache,
    get_paypal_transactions,
    load_paypal_cache,
)
from ..persistence.settings import load_capacities, load_paypal_settings
from .pdf_export import build_reconciliation_pdf


def _active(df: pd.DataFrame) -> pd.DataFrame:
    """Drop voided / refunded / cancelled rows."""
    if "status" not in df.columns:
        return df
    exclude = {"void", "voided", "refund", "refunded", "cancelled", "canceled"}
    return df[~df["status"].fillna("").str.lower().isin(exclude)]


def _paypal_ids_for_show(show_df: pd.DataFrame) -> set[str]:
    """
    Return the set of PayPal txn_ids that belong to this show.

    Includes:
    - Active tickets whose order was paid via PayPal
    - Voided tickets whose order was paid via PayPal with no refund issued
      (these are TT transfers: the original PayPal charge is still valid)
    """
    if "paypal_txn_id" not in show_df.columns:
        return set()

    # Active tickets — always included
    active  = _active(show_df)
    pp_ids  = set(active["paypal_txn_id"].dropna().astype(str).str.strip()) - {"", "nan"}

    # Voided tickets from PayPal orders that were transferred (not refunded)
    if "status" in show_df.columns and "_order_payment_type" in show_df.columns:
        voided_mask = show_df["status"].fillna("").str.lower().isin({"void", "voided"})
        paypal_mask = show_df["_order_payment_type"].fillna("").str.lower() == "paypal"
        no_refund_mask = (
            pd.to_numeric(show_df.get("_order_refund_amount", 0), errors="coerce").fillna(0) == 0
        )
        transferred = show_df[voided_mask & paypal_mask & no_refund_mask]
        pp_ids |= set(transferred["paypal_txn_id"].dropna().astype(str).str.strip()) - {"", "nan"}

    return pp_ids


def _filter_paypal_for_show(
    show_df: pd.DataFrame,
    paypal_txns: list[dict],
) -> list[dict]:
    """
    Return only the PayPal transactions that belong to this show, including:
    - Original payment transactions (txn_id in show's pp_ids)
    - Refund/reversal transactions (paypal_reference_id points to a show transaction)
    """
    if not paypal_txns:
        return []

    pp_ids = _paypal_ids_for_show(show_df)
    if not pp_ids:
        return paypal_txns  # nothing mapped yet — return all as fallback

    return [
        t for t in paypal_txns
        if t.get("txn_id", "") in pp_ids
        or t.get("paypal_reference_id", "") in pp_ids
    ]


def build_reconciliation(
    df: pd.DataFrame,
    paypal_txns: list[dict],
    show_filter: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Returns (totals_df, statistics_df, unmatched_pp_df).

    totals_df     — per-performance-date summary (mirrors the Totals sheet)
    statistics_df — ticket category breakdown per night (mirrors the Statistics sheet)
    unmatched_df  — PayPal transactions with no matching TT entry (flag for review)
    """
    show_df = df[df["show"] == show_filter].copy() if show_filter else df.copy()
    work = _active(show_df)

    show_txns   = _filter_paypal_for_show(show_df, paypal_txns)
    txn_by_ppid = {t["txn_id"]: t for t in show_txns}
    refund_by_orig = {
        t["paypal_reference_id"]: t
        for t in show_txns
        if t.get("paypal_reference_id")
    }

    # Voided-but-transferred tickets: original PayPal charge still valid, no refund issued.
    # Grouped separately so they contribute to PayPal totals without inflating ticket counts.
    transferred_voided = pd.DataFrame()
    if "_order_payment_type" in show_df.columns and "status" in show_df.columns:
        voided_mask    = show_df["status"].fillna("").str.lower().isin({"void", "voided"})
        paypal_mask    = show_df["_order_payment_type"].fillna("").str.lower() == "paypal"
        no_refund_mask = (
            pd.to_numeric(show_df.get("_order_refund_amount", 0), errors="coerce").fillna(0) == 0
        )
        transferred_voided = show_df[voided_mask & paypal_mask & no_refund_mask].copy()

    def _matched_txns_for_group(
        active_grp: pd.DataFrame,
        voided_grp: pd.DataFrame | None = None,
    ) -> list[dict]:
        seen, result = set(), []
        for grp in filter(lambda g: g is not None and not g.empty, [active_grp, voided_grp]):
            for pid in grp["paypal_txn_id"].dropna().astype(str).str.strip():
                if not pid or pid == "nan":
                    continue
                if pid in txn_by_ppid and pid not in seen:
                    result.append(txn_by_ppid[pid])
                    seen.add(pid)
                # Include the corresponding refund transaction if one exists
                if pid in refund_by_orig and refund_by_orig[pid]["txn_id"] not in seen:
                    result.append(refund_by_orig[pid])
                    seen.add(refund_by_orig[pid]["txn_id"])
        return result

    totals_rows = []
    if "performance_date" in work.columns:
        for perf_date, grp in work.groupby("performance_date", sort=True):
            # Include transferred-voided tickets for the same performance night
            vgrp = (
                transferred_voided[transferred_voided["performance_date"] == perf_date]
                if not transferred_voided.empty and "performance_date" in transferred_voided.columns
                else None
            )
            matched = _matched_txns_for_group(grp, vgrp) if show_txns else []

            if matched:
                gross     = sum(t["gross"] for t in matched)
                fees      = sum(t["fee"]   for t in matched)
                net       = sum(t["net"]   for t in matched)
                txn_count = len(matched)
            else:
                gross     = grp["revenue"].sum()
                fees      = 0.0
                net       = gross
                txn_count = int(grp["quantity"].sum())

            label = perf_date.strftime("%a %d %b %Y") if pd.notna(perf_date) else "Unknown"
            totals_rows.append({
                "Performance Date": label,
                "Transactions":     txn_count,
                "Gross (€)":        round(gross, 2),
                "Fees (€)":         round(fees, 2),
                "Net (€)":          round(net, 2),
            })

    if totals_rows:
        totals_df = pd.DataFrame(totals_rows)
        totals_df.loc["TOTAL"] = {
            "Performance Date": "Transactions Total",
            "Transactions":     totals_df["Transactions"].sum(),
            "Gross (€)":        totals_df["Gross (€)"].sum().round(2),
            "Fees (€)":         totals_df["Fees (€)"].sum().round(2),
            "Net (€)":          totals_df["Net (€)"].sum().round(2),
        }
    else:
        totals_df = pd.DataFrame(
            columns=["Performance Date", "Transactions", "Gross (€)", "Fees (€)", "Net (€)"]
        )

    stats_rows = []
    if "performance_date" in work.columns and "category" in work.columns:
        categories = sorted(work["category"].dropna().unique())
        for perf_date, grp in work.groupby("performance_date", sort=True):
            label = perf_date.strftime("%a %d %b %Y") if pd.notna(perf_date) else "Unknown"
            row = {"Performance Date": label, "Total Tickets": int(grp["quantity"].sum())}
            for cat in categories:
                row[cat] = int(grp[grp["category"] == cat]["quantity"].sum())
            stats_rows.append(row)

        if stats_rows:
            stats_df = pd.DataFrame(stats_rows)
            total_row = {"Performance Date": "Total", "Total Tickets": int(work["quantity"].sum())}
            for cat in categories:
                total_row[cat] = int(work[work["category"] == cat]["quantity"].sum())
            stats_df.loc["TOTAL"] = total_row
        else:
            stats_df = pd.DataFrame()
    else:
        stats_df = pd.DataFrame()

    # A show_txn is "matched" if:
    #   - its txn_id is a known PayPal txn for this show (active or transferred-voided), OR
    #   - it's a refund whose paypal_reference_id is a known PayPal txn for this show
    if show_txns:
        known_pp_ids = _paypal_ids_for_show(show_df)
        unmatched = [
            t for t in show_txns
            if t.get("txn_id", "")              not in known_pp_ids
            and t.get("paypal_reference_id", "") not in known_pp_ids
        ]
        unmatched_df = pd.DataFrame(unmatched) if unmatched else pd.DataFrame()
    else:
        unmatched_df = pd.DataFrame()

    return totals_df, stats_df, unmatched_df, show_txns


def render_reconciliation(df: pd.DataFrame, shows: list[str]) -> None:
    st.subheader("🧾 Reconciliation Report")
    st.markdown(
        "Generates **Totals** and **Statistics** tables for a selected production, "
        "cross-referenced with PayPal transaction data where available."
    )

    token_ready = bool(st.session_state.get("paypal_token"))
    if token_ready:
        env_label = "Sandbox" if st.session_state.get("paypal_sandbox") else "Live"
        st.caption(f"✓ PayPal connected · {env_label} (token active for this session)")
    else:
        pp_cid, _, _ = load_paypal_settings()
        if pp_cid:
            st.info("💡 PayPal credentials configured but no active token — go to ⚙️ Settings to connect.")
        else:
            st.info("💡 PayPal not configured — go to ⚙️ Settings to add credentials and connect.")

    st.divider()
    show = st.selectbox("Production to report", shows, key="recon_show")

    work     = _active(df)
    show_df  = work[work["show"] == show]
    today    = datetime.today()
    d_start  = today - timedelta(days=90)
    d_end    = today

    if "performance_date" in show_df.columns and not show_df["performance_date"].isna().all():
        dates   = pd.to_datetime(show_df["performance_date"], errors="coerce").dropna()
        if len(dates):
            d_start = dates.min().to_pydatetime() - timedelta(days=60)
            d_end   = dates.max().to_pydatetime() + timedelta(days=7)
    elif "date" in show_df.columns and not show_df["date"].isna().all():
        dates   = pd.to_datetime(show_df["date"], errors="coerce").dropna()
        if len(dates):
            d_start = dates.min().to_pydatetime() - timedelta(days=7)
            d_end   = dates.max().to_pydatetime() + timedelta(days=7)

    cd1, cd2 = st.columns(2)
    with cd1:
        pp_start = st.date_input("PayPal search from", value=d_start.date(), key="pp_start")
    with cd2:
        pp_end   = st.date_input("PayPal search to",   value=d_end.date(),   key="pp_end")

    cache_label = cache_status_label()
    if cache_label:
        cached_result = load_paypal_cache()
        if cached_result:
            _, c_start, c_end, _ = cached_result
            fully_covered = (pp_start >= c_start and pp_end <= c_end)
            if fully_covered:
                st.success(f"✓ Cache covers this date range — no API call needed.  \n📦 {cache_label}")
            else:
                missing_parts = []
                if pp_start < c_start:
                    missing_parts.append(f"{pp_start} → {c_start}")
                if pp_end > c_end:
                    missing_parts.append(f"{c_end} → {pp_end}")
                st.info(
                    f"📦 Cache: {cache_label}  \n"
                    f"⬇️ Will fetch missing portion(s): {', '.join(missing_parts)}"
                )
    else:
        st.info("📭 No PayPal cache yet — first load will fetch from the API and save locally.")

    paypal_txns: list[dict] = st.session_state.get("paypal_txns_cache", [])

    if not paypal_txns and cache_label:
        cached_result = load_paypal_cache()
        if cached_result:
            _, c_start, c_end, _ = cached_result
            if pp_start >= c_start and pp_end <= c_end:
                txns_from_cache = _in_range(cached_result[0], pp_start, pp_end)
                st.session_state["paypal_txns_cache"] = txns_from_cache
                paypal_txns = txns_from_cache

    cf1, cf2 = st.columns(2)
    with cf1:
        if st.button("📊 Generate Report"):
            cached_result = load_paypal_cache()
            if cached_result and pp_start >= cached_result[1] and pp_end <= cached_result[2]:
                txns = _in_range(cached_result[0], pp_start, pp_end)
                st.session_state["paypal_txns_cache"] = txns
                paypal_txns = txns
                st.success(f"Loaded {len(txns)} transactions from cache.")
            else:
                token   = st.session_state.get("paypal_token")
                sandbox = st.session_state.get("paypal_sandbox", False)
                if not token:
                    st.warning("Connect to PayPal first using 'Test & get token' above.")
                else:
                    env = "Sandbox" if sandbox else "Live"
                    with st.spinner(f"Loading PayPal transactions ({env})…"):
                        try:
                            txns = get_paypal_transactions(
                                token, pp_start, pp_end, sandbox, force_refresh=False
                            )
                            st.session_state["paypal_txns_cache"] = txns
                            paypal_txns = txns
                            st.success(f"Loaded {len(txns)} transactions for date range ({env}).")
                        except PermissionError as exc:
                            st.error(str(exc))
                        except Exception as exc:
                            st.error(f"Load failed ({env}): {exc}")
    with cf2:
        if st.button("🔄 Force refresh from API and Generate"):
            token   = st.session_state.get("paypal_token")
            saved_cid, saved_secret, saved_sandbox = load_paypal_settings()
            sandbox = st.session_state.get("paypal_sandbox", saved_sandbox)

            if not token:
                if not saved_cid or not saved_secret:
                    st.error("No PayPal credentials saved — configure them in ⚙️ Settings.")
                else:
                    with st.spinner("Connecting to PayPal…"):
                        ok, result = pp_get_token(saved_cid, saved_secret, saved_sandbox)
                    if ok:
                        token = result
                        st.session_state["paypal_token"]   = token
                        st.session_state["paypal_sandbox"] = saved_sandbox
                        sandbox = saved_sandbox
                    else:
                        st.error(f"Could not obtain PayPal token: {result}")

            if token:
                env = "Sandbox" if sandbox else "Live"
                with st.spinner(f"Fetching fresh from PayPal ({env})…"):
                    try:
                        txns = get_paypal_transactions(
                            token, pp_start, pp_end, sandbox, force_refresh=True
                        )
                        st.session_state["paypal_txns_cache"] = txns
                        paypal_txns = txns
                        st.success(f"Refreshed — {len(txns)} transactions ({env}).")
                    except PermissionError as exc:
                        st.error(str(exc))
                    except Exception as exc:
                        st.error(f"Refresh failed ({env}): {exc}")

    st.divider()
    totals_df, stats_df, unmatched_df, show_txns = build_reconciliation(
        df, paypal_txns, show_filter=show
    )

    st.markdown(f"### 💰 Totals — {show}")

    if show_txns:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Matched transactions", len(show_txns))
        m2.metric("Gross", f"€{sum(t['gross'] for t in show_txns):,.2f}")
        m3.metric("Fees",  f"€{sum(t['fee']   for t in show_txns):,.2f}")
        m4.metric("Net",   f"€{sum(t['net']   for t in show_txns):,.2f}")

    if not totals_df.empty:
        body  = totals_df.drop(index="TOTAL", errors="ignore")
        total = totals_df.loc[["TOTAL"]] if "TOTAL" in totals_df.index else pd.DataFrame()
        st.dataframe(body, use_container_width=True, hide_index=True)
        if not total.empty:
            st.markdown("**Totals**")
            st.dataframe(total, use_container_width=True, hide_index=True)
    else:
        st.info(
            "No performance date data found. "
            "Ensure the **performance_date** column is mapped and tickets have dates."
        )
        simple = (
            _active(df[df["show"] == show])
            .groupby("show")
            .agg(Tickets=("quantity", "sum"), Revenue=("revenue", "sum"))
            .reset_index()
        )
        st.dataframe(simple.style.format({"Revenue": "€{:.2f}"}), use_container_width=True)

    st.divider()
    st.markdown(f"### 🎟 Statistics — {show}")

    if not stats_df.empty:
        body_s  = stats_df.drop(index="TOTAL", errors="ignore")
        total_s = stats_df.loc[["TOTAL"]] if "TOTAL" in stats_df.index else pd.DataFrame()
        st.dataframe(body_s, use_container_width=True, hide_index=True)
        if not total_s.empty:
            st.markdown("**Totals**")
            st.dataframe(total_s, use_container_width=True, hide_index=True)

        cat_cols = [c for c in stats_df.columns if c not in ("Performance Date", "Total Tickets")]
        if cat_cols:
            plot_df = stats_df.drop(index="TOTAL", errors="ignore").copy()
            fig = px.bar(plot_df, x="Performance Date", y=cat_cols, barmode="stack",
                         title="Ticket categories per night",
                         labels={"value": "Tickets", "variable": "Category"})
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No category or performance date data available for the Statistics table.")

    tt_gross = _active(df[df["show"] == show])["revenue"].sum()
    pp_gross = sum(t["gross"] for t in show_txns) if show_txns else None

    # PDF download — covers Totals, Statistics, chart, and reconciliation summary
    if not totals_df.empty or not stats_df.empty:
        st.divider()
        with st.spinner("Building PDF…"):
            try:
                pdf_bytes = build_reconciliation_pdf(
                    show       = show,
                    pp_start   = pp_start,
                    pp_end     = pp_end,
                    totals_df  = totals_df,
                    stats_df   = stats_df,
                    show_txns  = show_txns,
                    tt_gross   = tt_gross,
                    pp_gross   = pp_gross,
                    show_df    = show_df,
                    capacity   = int(load_capacities().get(show, 0)),
                )
                safe_show = show.replace(" ", "_").replace("/", "-")
                st.download_button(
                    "⬇️ Download PDF Report",
                    data      = pdf_bytes,
                    file_name = f"{safe_show}_reconciliation.pdf",
                    mime      = "application/pdf",
                )
            except Exception as exc:
                st.error(f"PDF generation failed: {exc}")

    if show_txns:
        st.divider()
        st.markdown("### ✅ PayPal Reconciliation Check")
        diff = round(pp_gross - tt_gross, 2)

        ca, cb, cc = st.columns(3)
        ca.metric("Ticket Tailor gross", f"€{tt_gross:,.2f}")
        cb.metric("PayPal gross",        f"€{pp_gross:,.2f}")
        cc.metric("Difference", f"€{diff:,.2f}",
                  delta_color="normal" if abs(diff) < 0.02 else "inverse")

        if abs(diff) < 0.02:
            st.success("✓ Values match — reconciliation passed.")
        else:
            st.warning(
                f"⚠️ Difference of €{diff:.2f}. "
                "Check for refunds, fees, or transactions outside the date window."
            )

        if not unmatched_df.empty:
            st.markdown("**PayPal transactions with no matching Ticket Tailor entry:**")
            st.dataframe(unmatched_df, use_container_width=True, hide_index=True)
