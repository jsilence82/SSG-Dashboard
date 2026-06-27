"""Ticket category breakdown tab."""

import pandas as pd
import plotly.express as px
import streamlit as st


def render_category_overview(filtered: pd.DataFrame) -> None:
    by_cat   = (filtered.groupby("category", as_index=False)
                .agg(tickets=("quantity", "sum"), revenue=("revenue", "sum"))
                .sort_values("tickets", ascending=False))
    by_cat_show = filtered.groupby(["show", "category"], as_index=False)["quantity"].sum()
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(px.pie(by_cat, names="category", values="tickets",
                               title="Overall share of tickets by category"), width="stretch")
    with c2:
        st.plotly_chart(px.bar(by_cat_show, x="show", y="quantity", color="category",
                               title="Category mix per show",
                               labels={"quantity": "Tickets", "show": "Show"}), width="stretch")
