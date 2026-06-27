"""Top-line KPI metrics row."""

import pandas as pd
import streamlit as st


def render_kpis(filtered: pd.DataFrame) -> None:
    t  = filtered["quantity"].sum()
    r  = filtered["revenue"].sum()
    n  = filtered["show"].nunique()
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total tickets sold",   f"{t:,.0f}")
    k2.metric("Total revenue",        f"€{r:,.2f}")
    k3.metric("Shows",                f"{n}")
    k4.metric("Avg tickets / show",   f"{t/n:,.1f}" if n else "—")
    k5.metric("Avg revenue / ticket", f"€{r/t:,.2f}" if t else "—")
