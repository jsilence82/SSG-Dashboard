"""Multi-night analysis tab."""

import pandas as pd
import plotly.express as px
import streamlit as st

from ..config import DOW_ORDER
from ..i18n import t


def _night_label(pdate) -> str:
    """Format a performance datetime as 'Fri 7 Mar' — handles any datetime type."""
    try:
        ts = pd.Timestamp(pdate)
        return f"{ts.strftime('%a')} {ts.day} {ts.strftime('%b')}"
    except Exception:
        return str(pdate)


def render_multi_night(filtered: pd.DataFrame) -> None:
    has_occ   = ("occurrence" in filtered.columns and
                 filtered["occurrence"].replace("", pd.NA).notna().any())
    has_pdate = ("performance_date" in filtered.columns and
                 filtered["performance_date"].notna().any())

    if has_pdate:
        st.markdown(t("nights_by_dow"))
        all_perf = filtered[filtered["performance_date"].notna()].copy()
        all_perf["dow"] = all_perf["performance_date"].dt.day_name()

        by_dow = (all_perf.groupby("dow", as_index=False)
                  .agg(tickets=("quantity", "sum"), revenue=("revenue", "sum")))
        by_dow["order"] = by_dow["dow"].map({d: i for i, d in enumerate(DOW_ORDER)})
        by_dow = by_dow.sort_values("order").drop(columns="order")

        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(by_dow, x="dow", y="tickets",
                         title=t("tickets_by_dow"),
                         labels={"dow": t("day_label"), "tickets": t("tickets_label")},
                         text="tickets",
                         category_orders={"dow": DOW_ORDER})
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, width="stretch")
        with c2:
            fig2 = px.bar(by_dow, x="dow", y="revenue",
                          title=t("revenue_by_dow"),
                          labels={"dow": t("day_label"), "revenue": t("revenue_label")},
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
                       title=t("tickets_by_dow_per_show"),
                       labels={"dow": t("day_label"), "tickets": t("tickets_label"),
                               "show": t("show_label")},
                       category_orders={"dow": DOW_ORDER}),
                width="stretch")

        st.dataframe(by_dow.rename(columns={"dow": t("day_label"),
                                             "tickets": t("tickets_label"),
                                             "revenue": t("revenue_label")}),
                     width="stretch", hide_index=True)
        st.divider()

    if not has_occ and not has_pdate:
        st.info(t("no_occ_data"))
        return

    occ_data = filtered.copy()
    if has_occ:
        occ_data = occ_data[occ_data["occurrence"].replace("", pd.NA).notna()]

    occ_counts  = occ_data.groupby("show")["occurrence"].nunique() if has_occ else \
                  occ_data.groupby("show")["performance_date"].nunique()
    multi_shows = occ_counts[occ_counts > 1].index.tolist()

    if not multi_shows:
        st.info(t("no_multi_shows"))
        return

    selected = st.selectbox(t("select_show"), multi_shows, key="multinight_show")
    sd = occ_data[occ_data["show"] == selected].copy()

    if has_pdate and sd["performance_date"].notna().any():
        occ_perf = (sd[sd["performance_date"].notna()]
                    .groupby("occurrence")["performance_date"].first()
                    .sort_values())
        night_map   = {occ: _night_label(pdate) for occ, pdate in occ_perf.items()}
        night_order = [night_map[o] for o in occ_perf.index]
        for i, occ in enumerate(sd["occurrence"].unique()):
            if occ not in night_map:
                night_map[occ] = f"{t('night_prefix')} {i+1}"
    else:
        order_col = "date" if sd["date"].notna().any() else "occurrence"
        occ_order = (sd.groupby("occurrence")[order_col].min()
                     .sort_values().reset_index()["occurrence"])
        night_map   = {occ: f"{t('night_prefix')} {i+1}" for i, occ in enumerate(occ_order)}
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
                   title=f"{selected} — {t('tickets_per_night')}",
                   labels={"night": t("night_label"), "tickets": t("tickets_label")},
                   category_orders={"night": night_order}),
            width="stretch")
    with c2:
        st.plotly_chart(
            px.bar(by_night, x="night", y="revenue", text="revenue",
                   title=f"{selected} — {t('revenue_per_night')}",
                   labels={"night": t("night_label"), "revenue": t("revenue_label")},
                   category_orders={"night": night_order}),
            width="stretch")

    if sd["date"].notna().any():
        st.markdown(t("sales_velocity"))
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
                    title=f"{selected} — {t('cumulative_per_night')}",
                    labels={"day_number": t("day_number_x"),
                            "cumulative": t("cumulative_label"),
                            "night": t("night_label")},
                    category_orders={"night": night_order}),
            width="stretch")

    st.dataframe(by_night, width="stretch", hide_index=True)
