"""Sales-over-time trend tab."""

import pandas as pd
import plotly.express as px
import streamlit as st


def render_time_trend(filtered: pd.DataFrame) -> None:
    if not filtered["date"].notna().any():
        st.info("No valid dates in this dataset.")
        return
    ts = (filtered.dropna(subset=["date"])
          .assign(day=lambda d: d["date"].dt.normalize())
          .groupby(["show", "day"], as_index=False)
          .agg(tickets=("quantity", "sum"))
          .sort_values(["show", "day"]))
    ts["day_number"] = (ts["day"] - ts.groupby("show")["day"].transform("min")).dt.days
    ts["cumulative"] = ts.groupby("show")["tickets"].cumsum()

    all_shows = sorted(ts["show"].unique())
    st.markdown("**Shows displayed**")
    toggle_cols = st.columns(min(len(all_shows), 4))
    show_visible = {s: toggle_cols[i % len(toggle_cols)].checkbox(s, value=True,
                    key=f"trend_show_{s}") for i, s in enumerate(all_shows)}
    visible = [s for s, v in show_visible.items() if v]
    if not visible:
        st.warning("Select at least one show.")
        return
    ts_plot = ts[ts["show"].isin(visible)]
    view    = st.radio("View", ["Cumulative", "Daily"], horizontal=True, key="trend_view")
    y_col   = "cumulative" if view == "Cumulative" else "tickets"
    y_label = "Total tickets sold" if view == "Cumulative" else "Tickets sold"
    fig = px.line(ts_plot, x="day_number", y=y_col, color="show", markers=True,
                  title=f"Ticket sales — {view.lower()} (Day 0 = first sale per show)",
                  labels={"day_number": "Days since first sale", y_col: y_label, "show": "Show"})
    fig.update_layout(hovermode="x unified", xaxis=dict(dtick=1, tickmode="linear"))
    st.plotly_chart(fig, width="stretch")
    rows = []
    for show, grp in ts.groupby("show"):
        if show not in visible:  continue
        peak = grp.loc[grp["tickets"].idxmax()]
        rows.append({"Show": show, "First sale": grp["day"].min().date(),
                     "Last sale": grp["day"].max().date(),
                     "Selling window": f"{int(grp['day_number'].max())+1} days",
                     "Peak day": f"Day {int(peak['day_number'])} ({peak['day'].date()})",
                     "Peak tickets": int(peak["tickets"])})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
