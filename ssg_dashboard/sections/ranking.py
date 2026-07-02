"""Show ranking tab."""

import pandas as pd
import plotly.express as px
import streamlit as st

from ..i18n import t


def render_show_ranking(filtered: pd.DataFrame) -> None:
    all_cats = sorted(filtered["category"].unique())
    sel_cats = st.multiselect(t("filter_by_category"), all_cats,
                               default=[], key="ranking_cat_filter")
    rank_df  = filtered if not sel_cats else filtered[filtered["category"].isin(sel_cats)]
    by_show  = rank_df.groupby("show", as_index=False).agg(
        tickets=("quantity", "sum"), revenue=("revenue", "sum"))

    rank_options = [t("rank_tickets"), t("rank_revenue")]
    sort_by  = st.radio(t("rank_by"), rank_options, horizontal=True, key="rank_sort")
    sort_col = "tickets" if sort_by == t("rank_tickets") else "revenue"

    by_show  = by_show.sort_values(sort_col, ascending=False).reset_index(drop=True)
    by_show.insert(0, "Rank", range(1, len(by_show) + 1))
    label, color_col = (t("tickets_label"), "revenue") if sort_col == "tickets" else (t("revenue_label"), "tickets")
    fig = px.bar(by_show, x=sort_col, y="show", orientation="h", color=color_col,
                 color_continuous_scale="Blues",
                 labels={sort_col: label, "show": t("show_label")},
                 title=f"{t('show_label')}s ranked by {sort_by.lower()}"
                       + (f" — {', '.join(sel_cats)}" if sel_cats else ""),
                 text=sort_col)
    fig.update_yaxes(categoryorder="total ascending")
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig.update_layout(coloraxis_showscale=False, margin=dict(l=160))
    st.plotly_chart(fig, width="stretch")
    display = by_show.copy()
    display["revenue"] = display["revenue"].apply(lambda x: f"€{x:,.2f}")
    st.dataframe(display, width="stretch", hide_index=True)
