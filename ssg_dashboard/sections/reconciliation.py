"""Reconciliation report: Totals + Statistics tables cross-referenced with PayPal."""

from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from ..api.paypal import pp_get_token
from ..i18n import col_map, t
from ..persistence.paypal_cache import (
    _in_range,
    cache_status_label,
    clear_paypal_cache,
    get_paypal_transactions,
    load_paypal_cache,
)
from ..persistence.settings import load_capacities, load_paypal_settings, load_performance_dates
from .pdf_export import build_reconciliation_pdf


def _active(df: pd.DataFrame) -> pd.DataFrame:
    """Drop voided / refunded / cancelled rows."""
    if "status" not in df.columns:
        return df
    exclude = {"void", "voided", "refund", "refunded", "cancelled", "canceled"}
    return df[~df["status"].fillna("").str.lower().isin(exclude)]


def _paypal_only(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only tickets whose Ticket Tailor order was paid via PayPal.
    Used for PayPal transaction ID matching — not for gross totals."""
    if "_order_payment_type" not in df.columns:
        return df.iloc[0:0]
    return df[df["_order_payment_type"].fillna("").str.lower() == "paypal"]


def _exclude_operator(df: pd.DataFrame) -> pd.DataFrame:
    """Drop tickets paid via the 'operator' method (manually recorded by box-office
    staff — never processed through PayPal, so they have no corresponding PayPal
    transaction to reconcile against). All other types (paypal, no_cost, transfer,
    offline, stripe) flow through the same PayPal account and must be included."""
    if "_order_payment_type" not in df.columns:
        return df
    return df[df["_order_payment_type"].fillna("").str.lower() != "operator"]


def _parse_tt_date(value: str | None) -> datetime | None:
    """Parse a stored Ticket Tailor sale-window date (ISO 8601 string) into a datetime."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


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

    active  = _active(_paypal_only(show_df))
    pp_ids  = set(active["paypal_txn_id"].dropna().astype(str).str.strip()) - {"", "nan"}

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

    Internal column names are always English — callers rename for display.
    """
    show_df = df[df["show"] == show_filter].copy() if show_filter else df.copy()
    work = _active(_exclude_operator(show_df))

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
                if pid in refund_by_orig and refund_by_orig[pid]["txn_id"] not in seen:
                    result.append(refund_by_orig[pid])
                    seen.add(refund_by_orig[pid]["txn_id"])
        return result

    totals_rows = []
    if "performance_date" in work.columns:
        for perf_date, grp in work.groupby("performance_date", sort=True):
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
    st.subheader(t("recon_title"))
    st.markdown(t("recon_desc"))

    token_ready = bool(st.session_state.get("paypal_token"))
    if token_ready:
        env_label = "Sandbox" if st.session_state.get("paypal_sandbox") else "Live"
        st.caption(t("paypal_connected", env=env_label))
    else:
        pp_cid, _, _ = load_paypal_settings()
        if pp_cid:
            st.info(t("paypal_no_token"))
        else:
            st.info(t("paypal_not_configured"))

    st.divider()
    show = st.selectbox(t("production_to_report"), shows, key="recon_show")

    work     = _active(_exclude_operator(df))
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

    # Prefer the Ticket Tailor sale window (tickets_available_at → tickets_unavailable_at)
    # for this show when it's been fetched/saved — it's a precise bound, no padding needed.
    saved_window = {**st.session_state.get("api_performance_dates", {}), **load_performance_dates()}.get(show, {})
    sale_start   = _parse_tt_date(saved_window.get("tickets_available_at"))
    sale_end     = _parse_tt_date(saved_window.get("tickets_unavailable_at"))
    if sale_start:
        d_start = sale_start
    if sale_end:
        d_end = sale_end

    cd1, cd2 = st.columns(2)
    with cd1:
        pp_start = st.date_input(t("pp_search_from"), value=d_start.date(), key=f"pp_start_{show}")
    with cd2:
        pp_end   = st.date_input(t("pp_search_to"),   value=d_end.date(),   key=f"pp_end_{show}")

    cache_label = cache_status_label()
    if cache_label:
        cached_result = load_paypal_cache()
        if cached_result:
            _, c_start, c_end, _ = cached_result
            fully_covered = (pp_start >= c_start and pp_end <= c_end)
            if fully_covered:
                st.success(t("cache_covers", label=cache_label))
            else:
                missing_parts = []
                if pp_start < c_start:
                    missing_parts.append(f"{pp_start} → {c_start}")
                if pp_end > c_end:
                    missing_parts.append(f"{c_end} → {pp_end}")
                st.info(t("cache_partial", label=cache_label, parts=", ".join(missing_parts)))
    else:
        st.info(t("no_pp_cache"))

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
        if st.button(t("generate_report")):
            cached_result = load_paypal_cache()
            if cached_result and pp_start >= cached_result[1] and pp_end <= cached_result[2]:
                txns = _in_range(cached_result[0], pp_start, pp_end)
                st.session_state["paypal_txns_cache"] = txns
                paypal_txns = txns
                st.success(t("loaded_from_cache", n=len(txns)))
            else:
                token   = st.session_state.get("paypal_token")
                sandbox = st.session_state.get("paypal_sandbox", False)
                if not token:
                    st.warning(t("connect_paypal_first"))
                else:
                    env = "Sandbox" if sandbox else "Live"
                    with st.spinner(f"Loading PayPal transactions ({env})…"):
                        try:
                            txns = get_paypal_transactions(
                                token, pp_start, pp_end, sandbox, force_refresh=False
                            )
                            st.session_state["paypal_txns_cache"] = txns
                            paypal_txns = txns
                            st.success(t("loaded_transactions", n=len(txns), env=env))
                        except PermissionError as exc:
                            st.error(str(exc))
                        except Exception as exc:
                            st.error(t("load_failed", env=env, exc=exc))
    with cf2:
        if st.button(t("force_refresh")):
            token   = st.session_state.get("paypal_token")
            saved_cid, saved_secret, saved_sandbox = load_paypal_settings()
            sandbox = st.session_state.get("paypal_sandbox", saved_sandbox)

            if not token:
                if not saved_cid or not saved_secret:
                    st.error(t("no_pp_creds"))
                else:
                    with st.spinner(t("connecting_paypal")):
                        ok, result = pp_get_token(saved_cid, saved_secret, saved_sandbox)
                    if ok:
                        token = result
                        st.session_state["paypal_token"]   = token
                        st.session_state["paypal_sandbox"] = saved_sandbox
                        sandbox = saved_sandbox
                    else:
                        st.error(t("could_not_get_token", result=result))

            if token:
                env = "Sandbox" if sandbox else "Live"
                with st.spinner(f"Fetching fresh from PayPal ({env})…"):
                    try:
                        txns = get_paypal_transactions(
                            token, pp_start, pp_end, sandbox, force_refresh=True
                        )
                        st.session_state["paypal_txns_cache"] = txns
                        paypal_txns = txns
                        st.success(t("refreshed", n=len(txns), env=env))
                    except PermissionError as exc:
                        st.error(str(exc))
                    except Exception as exc:
                        st.error(t("refresh_failed", env=env, exc=exc))

    st.divider()
    totals_df, stats_df, unmatched_df, show_txns = build_reconciliation(
        df, paypal_txns, show_filter=show
    )

    st.markdown(t("totals_header", show=show))

    if show_txns:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(t("matched_transactions"), len(show_txns))
        m2.metric(t("gross"), f"€{sum(tx['gross'] for tx in show_txns):,.2f}")
        m3.metric(t("fees"),  f"€{sum(tx['fee']   for tx in show_txns):,.2f}")
        m4.metric(t("net"),   f"€{sum(tx['net']   for tx in show_txns):,.2f}")

    cmap = col_map()
    if not totals_df.empty:
        body  = totals_df.drop(index="TOTAL", errors="ignore").rename(columns=cmap)
        total = totals_df.loc[["TOTAL"]].rename(columns=cmap) if "TOTAL" in totals_df.index else pd.DataFrame()
        st.dataframe(body, width="stretch", hide_index=True)
        if not total.empty:
            st.markdown(t("totals_sub"))
            st.dataframe(total, width="stretch", hide_index=True)
    else:
        st.info(t("no_perf_date_data"))
        simple = (
            _active(_exclude_operator(df[df["show"] == show]))
            .groupby("show")
            .agg(Tickets=("quantity", "sum"), Revenue=("revenue", "sum"))
            .reset_index()
        )
        st.dataframe(simple.style.format({"Revenue": "€{:.2f}"}), width="stretch")

    st.divider()
    st.markdown(t("stats_header", show=show))

    if not stats_df.empty:
        body_s  = stats_df.drop(index="TOTAL", errors="ignore").rename(columns=cmap)
        total_s = stats_df.loc[["TOTAL"]].rename(columns=cmap) if "TOTAL" in stats_df.index else pd.DataFrame()
        st.dataframe(body_s, width="stretch", hide_index=True)
        if not total_s.empty:
            st.markdown(t("totals_sub"))
            st.dataframe(total_s, width="stretch", hide_index=True)

        cat_cols = [c for c in stats_df.columns if c not in ("Performance Date", "Total Tickets")]
        if cat_cols:
            plot_df = stats_df.drop(index="TOTAL", errors="ignore").copy()
            fig = px.bar(plot_df, x="Performance Date", y=cat_cols, barmode="stack",
                         title=t("tickets_per_category"),
                         labels={
                             "Performance Date": t("col_performance_date"),
                             "value": t("tickets_label"),
                             "variable": t("category_label"),
                         })
            st.plotly_chart(fig, width="stretch")
    else:
        st.info(t("no_category_data"))

    tt_gross = _active(_exclude_operator(df[df["show"] == show]))["revenue"].sum()
    pp_gross = sum(tx["gross"] for tx in show_txns) if show_txns else None

    if not totals_df.empty or not stats_df.empty:
        st.divider()
        with st.spinner(t("building_pdf")):
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
                    t("pdf_download"),
                    data      = pdf_bytes,
                    file_name = f"{safe_show}_reconciliation.pdf",
                    mime      = "application/pdf",
                )
            except Exception as exc:
                st.error(t("pdf_failed", exc=exc))

    if show_txns:
        st.divider()
        st.markdown(t("recon_check"))
        diff = round(pp_gross - tt_gross, 2)

        ca, cb, cc = st.columns(3)
        ca.metric(t("tt_gross_label"), f"€{tt_gross:,.2f}")
        cb.metric(t("pp_gross_label"), f"€{pp_gross:,.2f}")
        cc.metric(t("difference_label"), f"€{diff:,.2f}",
                  delta_color="normal" if abs(diff) < 0.02 else "inverse")

        if abs(diff) < 0.02:
            st.success(t("recon_passed"))
        else:
            st.warning(t("recon_diff_warning", diff=diff))
            excluded = (
                _active(df[df["show"] == show])
                .loc[lambda d: d["_order_payment_type"].fillna("").str.lower() == "operator"]
                .groupby("_order_payment_type")
                .agg(Tickets=("quantity", "sum"), Revenue=("revenue", "sum"))
                .reset_index()
                .rename(columns={"_order_payment_type": "Payment type"})
            )
            if not excluded.empty:
                st.caption(t("operator_excluded"))
                st.dataframe(excluded.style.format({"Revenue": "€{:.2f}"}),
                             width="stretch", hide_index=True)

        if not unmatched_df.empty:
            st.markdown(t("unmatched_header"))
            st.dataframe(unmatched_df, width="stretch", hide_index=True)
