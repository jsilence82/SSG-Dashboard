"""Show ranking tab."""

import pandas as pd
import plotly.express as px
import streamlit as st


def render_show_ranking(filtered: pd.DataFrame) -> None:
    all_cats = sorted(filtered["category"].unique())
    sel_cats = st.multiselect("Filter by category (blank = all)", all_cats,
                               default=[], key="ranking_cat_filter")
    rank_df  = filtered if not sel_cats else filtered[filtered["category"].isin(sel_cats)]
    by_show  = rank_df.groupby("show", as_index=False).agg(
        tickets=("quantity", "sum"), revenue=("revenue", "sum"))
    sort_by  = st.radio("Rank by", ["Tickets sold", "Revenue"], horizontal=True, key="rank_sort")
    sort_col = "tickets" if sort_by == "Tickets sold" else "revenue"
    by_show  = by_show.sort_values(sort_col, ascending=False).reset_index(drop=True)
    by_show.insert(0, "Rank", range(1, len(by_show) + 1))
    label, color_col = ("Tickets", "revenue") if sort_col == "tickets" else ("Revenue (€)", "tickets")
    fig = px.bar(by_show, x=sort_col, y="show", orientation="h", color=color_col,
                 color_continuous_scale="Blues",
                 labels={sort_col: label, "show": "Show"},
                 title=f"Shows ranked by {sort_by.lower()}"
                       + (f" — {', '.join(sel_cats)}" if sel_cats else ""),
                 text=sort_col)
    fig.update_yaxes(categoryorder="total ascending")
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig.update_layout(coloraxis_showscale=False, margin=dict(l=160))
    st.plotly_chart(fig, width="stretch")
    display = by_show.copy()
    display["revenue"] = display["revenue"].apply(lambda x: f"€{x:,.2f}")
    st.dataframe(display, width="stretch", hide_index=True)
