"""Detail table tab and export buttons."""

import io

import pandas as pd
import streamlit as st


def render_detail_table(filtered: pd.DataFrame, by_show: pd.DataFrame,
                        by_category: pd.DataFrame) -> None:
    detail = (filtered.groupby(["show", "category"], as_index=False)
              .agg(tickets=("quantity", "sum"), revenue=("revenue", "sum"))
              .sort_values(["show", "tickets"], ascending=[True, False]))
    detail["avg_price"] = (detail["revenue"] / detail["tickets"]).round(2)
    st.dataframe(detail, width="stretch", hide_index=True)
    csv = detail.to_csv(index=False).encode("utf-8")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        detail.to_excel(w, index=False, sheet_name="Breakdown")
        by_show.to_excel(w, index=False, sheet_name="By show")
        by_category.to_excel(w, index=False, sheet_name="By category")
    e1, e2 = st.columns(2)
    e1.download_button("⬇ CSV",   csv, "ssg_tickets.csv",   "text/csv")
    e2.download_button("⬇ Excel", buf.getvalue(), "ssg_tickets.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
