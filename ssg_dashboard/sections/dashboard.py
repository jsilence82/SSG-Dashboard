"""Master render: filters, KPIs, and tab assembly."""

import pandas as pd
import streamlit as st

from .kpis import render_kpis
from .overview import render_overview_bars, render_per_show_pies
from .ranking import render_show_ranking
from .categories import render_category_overview
from .trend import render_time_trend
from .yield_capacity import render_yield_capacity
from .repeat_buyers import render_repeat_buyers
from .multi_night import render_multi_night
from .detail import render_detail_table
from .reconciliation import render_reconciliation
from .settings import render_settings


def render_dashboard(data: pd.DataFrame, capacity_by_show: dict) -> None:
    section = st.tabs(["📊 Analytics", "🧾 Reconciliation Report", "⚙️ Settings"])

    with section[0]:
        _render_analytics(data, capacity_by_show)

    with section[1]:
        shows = sorted(data["show"].dropna().unique().tolist())
        render_reconciliation(data, shows)

    with section[2]:
        render_settings()


def _render_analytics(data: pd.DataFrame, capacity_by_show: dict) -> None:
    st.subheader("Filters")
    f1, f2 = st.columns([2, 1])
    with f1:
        shows = sorted(data["show"].unique())
        sel_shows = st.multiselect("Shows to include", shows, default=shows)
    with f2:
        if data["status"].nunique() > 1 or data["status"].iloc[0] != "unknown":
            statuses      = sorted(data["status"].unique())
            default_stati = [s for s in statuses if "void" not in s.lower()] or statuses
            sel_stati     = st.multiselect("Statuses", statuses, default=default_stati)
        else:
            sel_stati = data["status"].unique().tolist()

    filtered = data[data["show"].isin(sel_shows) & data["status"].isin(sel_stati)]
    if filtered.empty:
        st.warning("No rows match the current filters.")
        return

    render_kpis(filtered)
    st.divider()

    tabs = st.tabs(["📊 Overview", "🥧 Per-show breakdown", "🏆 Show ranking",
                    "🎟 Categories", "📈 Sales trend", "💺 Yield & Capacity",
                    "🔄 Repeat buyers", "🌙 Multi-night", "📋 Detail table"])

    by_show = (filtered.groupby("show", as_index=False)
               .agg(tickets=("quantity", "sum"), revenue=("revenue", "sum"))
               .sort_values("tickets", ascending=False))
    by_cat  = (filtered.groupby("category", as_index=False)
               .agg(tickets=("quantity", "sum"), revenue=("revenue", "sum"))
               .sort_values("tickets", ascending=False))

    with tabs[0]:  render_overview_bars(filtered)
    with tabs[1]:  render_per_show_pies(filtered)
    with tabs[2]:  render_show_ranking(filtered)
    with tabs[3]:
        st.subheader("Ticket categories")
        render_category_overview(filtered)
    with tabs[4]:
        st.subheader("Sales over time")
        render_time_trend(filtered)
    with tabs[5]:
        st.subheader("Yield & Capacity")
        render_yield_capacity(filtered, capacity_by_show)
    with tabs[6]:
        st.subheader("Audience Retention")
        render_repeat_buyers(filtered)
    with tabs[7]:
        st.subheader("Multi-night Analysis")
        render_multi_night(filtered)
    with tabs[8]:
        st.subheader("Detail table")
        render_detail_table(filtered, by_show, by_cat)
