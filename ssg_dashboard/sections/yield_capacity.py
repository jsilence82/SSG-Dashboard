"""Yield & capacity tab."""

import pandas as pd
import plotly.express as px
import streamlit as st

from ..persistence.settings import save_capacities


def render_yield_capacity(filtered: pd.DataFrame, capacity_by_show: dict) -> None:
    shows = sorted(filtered["show"].unique())

    st.markdown("**Capacity per show** — enter total seats available. "
                "Values are saved and pre-filled from the API when available.")

    n_cap_cols = min(3, len(shows))
    cap_cols   = st.columns(n_cap_cols)
    updated    = {}
    for i, show in enumerate(shows):
        with cap_cols[i % n_cap_cols]:
            updated[show] = st.number_input(
                show, min_value=0,
                value=int(capacity_by_show.get(show, 0)),
                step=1, key=f"cap_{i}")

    if st.button("💾 Save capacities"):
        save_capacities(updated)
        st.success("Capacities saved.")

    valid = {s: c for s, c in updated.items() if c > 0}
    if not valid:
        st.info("Enter capacity above to unlock yield metrics.")
        return

    by_show = (filtered.groupby("show", as_index=False)
               .agg(tickets=("quantity", "sum"), revenue=("revenue", "sum")))
    by_show["capacity"]     = by_show["show"].map(updated).fillna(0).astype(int)
    by_show["sell_through"] = (by_show["tickets"] / by_show["capacity"] * 100).round(1)
    by_show["rev_per_seat"] = (by_show["revenue"] / by_show["capacity"]).round(2)
    by_show = by_show[by_show["capacity"] > 0].sort_values("sell_through", ascending=False)

    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(by_show, x="show", y="sell_through",
                     title="Sell-through rate (%)",
                     labels={"show": "Show", "sell_through": "%"}, text="sell_through")
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="Full house")
        st.plotly_chart(fig, width="stretch")
    with c2:
        fig2 = px.bar(by_show.sort_values("rev_per_seat", ascending=False),
                      x="show", y="rev_per_seat",
                      title="Revenue per available seat (€)",
                      labels={"show": "Show", "rev_per_seat": "€ / seat"}, text="rev_per_seat")
        fig2.update_traces(texttemplate="€%{text:.2f}", textposition="outside")
        st.plotly_chart(fig2, width="stretch")

    display = by_show.copy()
    display["revenue"]      = display["revenue"].apply(lambda x: f"€{x:,.2f}")
    display["rev_per_seat"] = display["rev_per_seat"].apply(lambda x: f"€{x:.2f}")
    display["sell_through"] = display["sell_through"].apply(lambda x: f"{x:.1f}%")
    st.dataframe(display[["show", "capacity", "tickets", "sell_through",
                           "revenue", "rev_per_seat"]], width="stretch", hide_index=True)
