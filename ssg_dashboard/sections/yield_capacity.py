"""Yield & capacity tab."""

from datetime import date, datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from ..i18n import t
from ..persistence.settings import save_capacities, save_performance_dates


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def render_yield_capacity(filtered: pd.DataFrame, capacity_by_show: dict,
                           performance_dates_by_show: dict | None = None) -> None:
    shows = sorted(filtered["show"].unique())

    st.markdown(t("capacity_per_show"))

    n_cap_cols = min(3, len(shows))
    cap_cols   = st.columns(n_cap_cols)
    updated    = {}
    for i, show in enumerate(shows):
        with cap_cols[i % n_cap_cols]:
            updated[show] = st.number_input(
                show, min_value=0,
                value=int(capacity_by_show.get(show, 0)),
                step=1, key=f"cap_{i}")

    if st.button(t("save_capacities")):
        save_capacities(updated)
        st.success(t("capacities_saved"))

    st.divider()
    st.markdown(t("ticket_sale_window"))

    performance_dates_by_show = performance_dates_by_show or {}
    updated_dates = {}
    for show in shows:
        saved = performance_dates_by_show.get(show, {})
        dc1, dc2 = st.columns(2)
        with dc1:
            start = st.date_input(
                f"{show} — {t('on_sale_from')}",
                value=_parse_date(saved.get("tickets_available_at")),
                key=f"perf_start_{show}")
        with dc2:
            end = st.date_input(
                f"{show} — {t('event_ended')}",
                value=_parse_date(saved.get("tickets_unavailable_at")),
                key=f"perf_end_{show}")
        if start or end:
            updated_dates[show] = {
                "tickets_available_at":   start.isoformat() if start else None,
                "tickets_unavailable_at": end.isoformat() if end else None,
            }

    if st.button(t("save_perf_dates")):
        save_performance_dates(updated_dates)
        st.success(t("perf_dates_saved"))

    valid = {s: c for s, c in updated.items() if c > 0}
    if not valid:
        st.info(t("enter_capacity"))
        return

    by_show = (filtered.groupby("show", as_index=False)
               .agg(tickets=("quantity", "sum"), revenue=("revenue", "sum")))
    by_show["capacity"]     = by_show["show"].map(updated).fillna(0).astype(int)
    by_show["sell_through"] = (by_show["tickets"] / by_show["capacity"] * 100).round(1)
    by_show["rev_per_seat"] = (by_show["revenue"] / by_show["capacity"]).round(2)
    by_show = by_show[by_show["capacity"] > 0].sort_values("sell_through", ascending=False)

    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(by_show, x="show", y="sell_through",
                     title=t("sell_through_rate"),
                     labels={"show": t("show_label"), "sell_through": t("percent_label")},
                     text="sell_through")
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.add_hline(y=100, line_dash="dash", line_color="red",
                      annotation_text=t("full_house"))
        st.plotly_chart(fig, width="stretch")
    with c2:
        fig2 = px.bar(by_show.sort_values("rev_per_seat", ascending=False),
                      x="show", y="rev_per_seat",
                      title=t("rev_per_seat_title"),
                      labels={"show": t("show_label"), "rev_per_seat": t("seat_label")},
                      text="rev_per_seat")
        fig2.update_traces(texttemplate="€%{text:.2f}", textposition="outside")
        st.plotly_chart(fig2, width="stretch")

    display = by_show.copy()
    display["revenue"]      = display["revenue"].apply(lambda x: f"€{x:,.2f}")
    display["rev_per_seat"] = display["rev_per_seat"].apply(lambda x: f"€{x:.2f}")
    display["sell_through"] = display["sell_through"].apply(lambda x: f"{x:.1f}%")
    st.dataframe(display[["show", "capacity", "tickets", "sell_through",
                           "revenue", "rev_per_seat"]], width="stretch", hide_index=True)
