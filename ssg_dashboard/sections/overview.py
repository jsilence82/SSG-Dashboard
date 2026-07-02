"""Overview tab: per-show bars and per-show category pies."""

import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from ..i18n import t


def render_overview_bars(filtered: pd.DataFrame) -> None:
    by_show = (filtered.groupby("show", as_index=False)
               .agg(tickets=("quantity", "sum"), revenue=("revenue", "sum"))
               .sort_values("tickets", ascending=False))
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(px.bar(by_show, x="show", y="tickets",
                               title=t("tickets_sold_per_show"),
                               labels={"show": t("show_label"), "tickets": t("tickets_label")}),
                        width="stretch")
    with c2:
        st.plotly_chart(px.bar(by_show, x="show", y="revenue",
                               title=t("revenue_per_show"),
                               labels={"show": t("show_label"), "revenue": t("revenue_label")}),
                        width="stretch")


def render_per_show_pies(filtered: pd.DataFrame) -> None:
    shows  = sorted(filtered["show"].unique())
    n_cols = min(3, len(shows))
    n_rows = math.ceil(len(shows) / n_cols)
    fig = make_subplots(rows=n_rows, cols=n_cols,
                        specs=[[{"type": "pie"}] * n_cols for _ in range(n_rows)],
                        subplot_titles=shows)
    for idx, show in enumerate(shows):
        sd = filtered[filtered["show"] == show].groupby("category", as_index=False)["quantity"].sum()
        fig.add_trace(go.Pie(labels=sd["category"], values=sd["quantity"], name=show,
                             textinfo="label+percent", showlegend=False),
                      row=idx // n_cols + 1, col=idx % n_cols + 1)
    fig.update_layout(height=320 * n_rows, margin=dict(t=60, b=20))
    st.plotly_chart(fig, width="stretch")
