"""Top-line KPI metrics row."""

import pandas as pd
import streamlit as st

from ..i18n import t


def render_kpis(filtered: pd.DataFrame) -> None:
    total_tickets = filtered["quantity"].sum()
    total_revenue = filtered["revenue"].sum()
    n = filtered["show"].nunique()
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric(t("kpi_total_tickets"),   f"{total_tickets:,.0f}")
    k2.metric(t("kpi_total_revenue"),   f"€{total_revenue:,.2f}")
    k3.metric(t("kpi_shows"),           f"{n}")
    k4.metric(t("kpi_avg_tickets"),     f"{total_tickets/n:,.1f}" if n else "—")
    k5.metric(t("kpi_avg_revenue"),     f"€{total_revenue/total_tickets:,.2f}" if total_tickets else "—")
