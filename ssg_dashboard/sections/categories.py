"""Ticket category breakdown tab."""

import pandas as pd
import plotly.express as px
import streamlit as st

from ..i18n import t


def render_category_overview(filtered: pd.DataFrame) -> None:
    by_cat      = (filtered.groupby("category", as_index=False)
                   .agg(tickets=("quantity", "sum"), revenue=("revenue", "sum"))
                   .sort_values("tickets", ascending=False))
    by_cat_show = filtered.groupby(["show", "category"], as_index=False)["quantity"].sum()
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(px.pie(by_cat, names="category", values="tickets",
                               title=t("ticket_share_by_cat")), width="stretch")
    with c2:
        st.plotly_chart(px.bar(by_cat_show, x="show", y="quantity", color="category",
                               title=t("category_mix_per_show"),
                               labels={"quantity": t("quantity_label"),
                                       "show": t("show_label"),
                                       "category": t("category_label")}),
                        width="stretch")
