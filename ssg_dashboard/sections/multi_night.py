"""Multi-night analysis tab."""

import pandas as pd
import plotly.express as px
import streamlit as st

from ..config import DOW_ORDER


def _night_label(pdate) -> str:
    """Format a performance datetime as 'Fri 7 Mar' — handles any datetime type."""
    try:
        ts = pd.Timestamp(pdate)  # normalises numpy datetime64, pd.Timestamp, strings
        return f"{ts.strftime('%a')} {ts.day} {ts.strftime('%b')}"
    except Exception:
        return str(pdate)


def render_multi_night(filtered: pd.DataFrame) -> None:
    has_occ   = ("occurrence" in filtered.columns and
                 filtered["occurrence"].replace("", pd.NA).notna().any())
    has_pdate = ("performance_date" in filtered.columns and
                 filtered["performance_date"].notna().any())

    if has_pdate:
        st.markdown("### Nights by day of week — all shows")
        all_perf = filtered[filtered["performance_date"].notna()].copy()
        all_perf["dow"] = all_perf["performance_date"].dt.day_name()

        by_dow = (all_perf.groupby("dow", as_index=False)
                  .agg(tickets=("quantity", "sum"), revenue=("revenue", "sum")))
        by_dow["order"] = by_dow["dow"].map({d: i for i, d in enumerate(DOW_ORDER)})
        by_dow = by_dow.sort_values("order").drop(columns="order")

        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(by_dow, x="dow", y="tickets",
                         title="Tickets sold by day of week",
                         labels={"dow": "Day", "tickets": "Tickets"},
                         text="tickets",
                         category_orders={"dow": DOW_ORDER})
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, width="stretch")
        with c2:
            fig2 = px.bar(by_dow, x="dow", y="revenue",
                          title="Revenue by day of week",
                          labels={"dow": "Day", "revenue": "Revenue (€)"},
                          text="revenue",
                          category_orders={"dow": DOW_ORDER})
            fig2.update_traces(texttemplate="€%{text:,.0f}", textposition="outside")
            st.plotly_chart(fig2, width="stretch")

        if filtered["show"].nunique() > 1:
            perf_by_show = (all_perf.groupby(["show", "dow"], as_index=False)
                            .agg(tickets=("quantity", "sum")))
            st.plotly_chart(
                px.bar(perf_by_show, x="dow", y="tickets", color="show",
                       barmode="group",
                       title="Tickets by day of week, per show",
                       labels={"dow": "Day", "tickets": "Tickets", "show": "Show"},
                       category_orders={"dow": DOW_ORDER}),
                width="stretch")

        st.dataframe(by_dow.rename(columns={"dow": "Day", "tickets": "Tickets",
                                             "revenue": "Revenue (€)"}),
                     width="stretch", hide_index=True)
        st.divider()

    if not has_occ and not has_pdate:
        st.info("Map an occurrence ID or performance date column to enable multi-night analysis. "
                "In Ticket Tailor data, occurrence maps to the `event_id` field.")
        return

    occ_data = filtered.copy()
    if has_occ:
        occ_data = occ_data[occ_data["occurrence"].replace("", pd.NA).notna()]

    occ_counts  = occ_data.groupby("show")["occurrence"].nunique() if has_occ else \
                  occ_data.groupby("show")["performance_date"].nunique()
    multi_shows = occ_counts[occ_counts > 1].index.tolist()

    if not multi_shows:
        st.info("No shows with multiple nights found in the current data.")
        return

    selected = st.selectbox("Select show", multi_shows, key="multinight_show")
    sd = occ_data[occ_data["show"] == selected].copy()

    if has_pdate and sd["performance_date"].notna().any():
        occ_perf = (sd[sd["performance_date"].notna()]
                    .groupby("occurrence")["performance_date"].first()
                    .sort_values())
        night_map   = {occ: _night_label(pdate) for occ, pdate in occ_perf.items()}
        night_order = [night_map[o] for o in occ_perf.index]
        for i, occ in enumerate(sd["occurrence"].unique()):
            if occ not in night_map:
                night_map[occ] = f"Night {i+1}"
    else:
        order_col = "date" if sd["date"].notna().any() else "occurrence"
        occ_order = (sd.groupby("occurrence")[order_col].min()
                     .sort_values().reset_index()["occurrence"])
        night_map   = {occ: f"Night {i+1}" for i, occ in enumerate(occ_order)}
        night_order = list(occ_order.map(night_map))

    sd["night"] = sd["occurrence"].map(night_map)

    by_night = (sd.groupby("night", as_index=False)
                .agg(tickets=("quantity", "sum"), revenue=("revenue", "sum"))
                .sort_values("night", key=lambda s: s.map(
                    {n: i for i, n in enumerate(night_order)})))

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(
            px.bar(by_night, x="night", y="tickets", text="tickets",
                   title=f"{selected} — tickets per night",
                   labels={"night": "Night", "tickets": "Tickets"},
                   category_orders={"night": night_order}),
            width="stretch")
    with c2:
        st.plotly_chart(
            px.bar(by_night, x="night", y="revenue", text="revenue",
                   title=f"{selected} — revenue per night",
                   labels={"night": "Night", "revenue": "Revenue (€)"},
                   category_orders={"night": night_order}),
            width="stretch")

    if sd["date"].notna().any():
        st.markdown("**Sales velocity — which night sold fastest?**")
        ts = (sd.dropna(subset=["date"])
              .assign(day=lambda d: d["date"].dt.normalize())
              .groupby(["night", "day"], as_index=False)
              .agg(tickets=("quantity", "sum"))
              .sort_values(["night", "day"]))
        ts["day_number"] = (ts["day"]
                            - ts.groupby("night")["day"].transform("min")).dt.days
        ts["cumulative"] = ts.groupby("night")["tickets"].cumsum()
        st.plotly_chart(
            px.line(ts, x="day_number", y="cumulative", color="night", markers=True,
                    title=f"{selected} — cumulative sales per night "
                          "(Day 0 = first sale per night)",
                    labels={"day_number": "Days since first sale",
                            "cumulative": "Tickets sold", "night": "Night"},
                    category_orders={"night": night_order}),
            width="stretch")

    st.dataframe(by_night, width="stretch", hide_index=True)
