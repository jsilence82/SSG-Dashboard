"""Audience retention / repeat buyers tab."""

import pandas as pd
import plotly.express as px
import streamlit as st

from ..i18n import t


def render_repeat_buyers(filtered: pd.DataFrame) -> None:
    has_identity = ("buyer_id" in filtered.columns and
                    filtered["buyer_id"].replace("", pd.NA).notna().any())
    if not has_identity:
        st.info(t("map_buyer_column"))
        return

    em = filtered[filtered["buyer_id"].notna() & (filtered["buyer_id"] != "")]
    if em.empty:
        st.info(t("no_buyer_ids"))
        return

    shows_per_buyer = em.groupby("buyer_id")["show"].nunique()
    total   = len(shows_per_buyer)
    repeat  = (shows_per_buyer >= 2).sum()
    loyal   = (shows_per_buyer >= 3).sum()

    k1, k2, k3 = st.columns(3)
    k1.metric(t("unique_buyers"),      f"{total:,}")
    k2.metric(t("repeat_buyers_2plus"), f"{repeat:,}",
              f"{repeat/total*100:.1f}%" if total else None)
    k3.metric(t("loyal_buyers_3plus"),  f"{loyal:,}",
              f"{loyal/total*100:.1f}%" if total else None)

    c1, c2 = st.columns(2)
    with c1:
        hist = (shows_per_buyer.value_counts().sort_index()
                .reset_index().rename(columns={"count": "buyers",
                                               "show": "shows_attended"}))
        hist.columns = ["shows_attended", "buyers"]
        hist["shows_attended"] = hist["shows_attended"].astype(str) + " show(s)"
        st.plotly_chart(
            px.bar(hist, x="shows_attended", y="buyers",
                   title=t("shows_attended_title"),
                   labels={"shows_attended": t("shows_attended_x"),
                           "buyers": t("buyers_label")}),
            width="stretch")

    with c2:
        if em["date"].notna().any():
            show_order = (em.groupby("show")["date"].min()
                          .sort_values().index.tolist())
        else:
            show_order = sorted(em["show"].unique())

        # A buyer counts as "repeat" for a show if they attended any other
        # show at all (looking both forward and backward in time) — not just
        # shows that happened earlier. Otherwise the earliest show in the
        # dataset would always show zero repeat buyers by construction.
        repeat_ids = set(shows_per_buyer[shows_per_buyer >= 2].index)

        rows = []
        for show in show_order:
            buyers_this_show = set(em[em["show"] == show]["buyer_id"])
            repeat_count = len(buyers_this_show & repeat_ids)
            single_count = len(buyers_this_show) - repeat_count
            rows.append({
                t("show_label"):           show,
                t("single_show_buyers"):   single_count,
                t("repeat_buyers_label"):  repeat_count,
                "Repeat rate":             f"{repeat_count/len(buyers_this_show)*100:.0f}%"
                                           if buyers_this_show else "—",
            })

        ret_df = pd.DataFrame(rows)
        melted = ret_df.melt(
            id_vars=t("show_label"),
            value_vars=[t("single_show_buyers"), t("repeat_buyers_label")],
        )
        st.plotly_chart(
            px.bar(melted, x=t("show_label"), y="value", color="variable",
                   title=t("single_vs_repeat"),
                   labels={"value": t("buyers_label"), "variable": ""}),
            width="stretch")

    st.dataframe(ret_df, width="stretch", hide_index=True)
