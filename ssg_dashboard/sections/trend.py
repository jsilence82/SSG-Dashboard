"""Sales-over-time trend tab."""

import pandas as pd
import plotly.express as px
import streamlit as st

from ..i18n import t


def render_time_trend(filtered: pd.DataFrame) -> None:
    if not filtered["date"].notna().any():
        st.info(t("no_valid_dates"))
        return
    ts = (filtered.dropna(subset=["date"])
          .assign(day=lambda d: d["date"].dt.normalize())
          .groupby(["show", "day"], as_index=False)
          .agg(tickets=("quantity", "sum"))
          .sort_values(["show", "day"]))
    ts["day_number"] = (ts["day"] - ts.groupby("show")["day"].transform("min")).dt.days
    ts["cumulative"] = ts.groupby("show")["tickets"].cumsum()

    all_shows = sorted(ts["show"].unique())
    st.markdown(t("shows_displayed"))
    toggle_cols = st.columns(min(len(all_shows), 4))
    show_visible = {s: toggle_cols[i % len(toggle_cols)].checkbox(s, value=True,
                    key=f"trend_show_{s}") for i, s in enumerate(all_shows)}
    visible = [s for s, v in show_visible.items() if v]
    if not visible:
        st.warning(t("select_at_least_one"))
        return
    ts_plot = ts[ts["show"].isin(visible)]

    view_options = [t("view_cumulative"), t("view_daily")]
    view    = st.radio("View", view_options, horizontal=True, key="trend_view")
    is_cumulative = (view == t("view_cumulative"))
    y_col   = "cumulative" if is_cumulative else "tickets"
    y_label = t("total_tickets_y") if is_cumulative else t("daily_tickets_y")

    fig = px.line(ts_plot, x="day_number", y=y_col, color="show", markers=True,
                  title=f"Ticket sales — {view.lower()} (Day 0 = first sale per show)",
                  labels={"day_number": t("day_number_x"), y_col: y_label, "show": t("show_label")})
    fig.update_layout(hovermode="x unified", xaxis=dict(dtick=1, tickmode="linear"))
    st.plotly_chart(fig, width="stretch")

    rows = []
    for show, grp in ts.groupby("show"):
        if show not in visible:  continue
        peak = grp.loc[grp["tickets"].idxmax()]
        rows.append({
            t("show_label"):          show,
            t("first_sale_col"):      grp["day"].min().date(),
            t("last_sale_col"):       grp["day"].max().date(),
            t("selling_window_col"):  f"{int(grp['day_number'].max())+1} {t('days_suffix')}",
            t("peak_day_col"):        f"{t('day_prefix')} {int(peak['day_number'])} ({peak['day'].date()})",
            t("peak_tickets_col"):    int(peak["tickets"]),
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
