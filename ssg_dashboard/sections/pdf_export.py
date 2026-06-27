"""PDF export for the reconciliation report."""

import io
import os
from datetime import date, datetime

import pandas as pd
from fpdf import FPDF

_M      = 15    # page margin mm
_CW     = 267   # content width for A4 landscape (297 - 2×15)
_ROW_H  = 6     # table row height mm
_HEAD_H = 7     # header row height mm

# Explicit chart palette — avoids kaleido colour rendering issues with px defaults
_CHART_COLORS = [
    "#4472C4", "#ED7D31", "#70AD47", "#FFC000",
    "#5B9BD5", "#A9D18E", "#FF0000", "#7030A0",
]

_COL_HEADER_BG  = (45,  85, 135)
_COL_HEADER_FG  = (255, 255, 255)
_COL_ALT_BG     = (240, 244, 250)
_COL_WHITE      = (255, 255, 255)
_COL_TOTAL_BG   = (210, 225, 210)
_COL_BORDER     = (180, 180, 180)
_COL_SECTION_FG = (45,  85, 135)
_COL_BODY       = (30,  30,  30)
_COL_MUTED      = (100, 100, 100)
_COL_PASS_BG    = (220, 240, 220)
_COL_FAIL_BG    = (250, 225, 200)

_FONT_CANDIDATES = [
    # macOS
    ("/Library/Fonts/Arial Unicode.ttf",                              None),
    ("/System/Library/Fonts/Supplemental/Arial.ttf",
     "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    # Windows
    ("C:/Windows/Fonts/arialuni.ttf",  None),
    ("C:/Windows/Fonts/arial.ttf",     "C:/Windows/Fonts/arialbd.ttf"),
    # Linux
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
]


def _register_fonts(pdf: FPDF) -> str:
    """Register a Unicode TTF font pair and return the family name, or 'Helvetica'."""
    for regular, bold in _FONT_CANDIDATES:
        if os.path.exists(regular):
            pdf.add_font("U", "", regular)
            # Use the bold variant if available, otherwise register the same file
            bold_path = bold if bold and os.path.exists(bold) else regular
            pdf.add_font("U", "B", bold_path)
            return "U"
    return "Helvetica"


def _safe(text: str, family: str) -> str:
    """Substitute non-Latin-1 chars when falling back to Helvetica core font."""
    if family != "Helvetica":
        return text
    return (text
            .replace("→", "->")
            .replace("—", "-")
            .replace("✓", "OK:")
            .replace("⚠", "!")
            .replace("€", "EUR "))


class _PDF(FPDF):
    def __init__(self, show: str, family: str):
        super().__init__(orientation="L", format="A4")
        self._show   = show
        self._family = family
        self.set_margins(_M, _M, _M)
        self.set_auto_page_break(auto=True, margin=20)

    def _f(self, text: str) -> str:
        return _safe(text, self._family)

    def header(self):
        self.set_font(self._family, "B", 9)
        self.set_text_color(*_COL_MUTED)
        self.cell(0, 6, self._f(f"SSG Ticket Sales Dashboard  ·  {self._show}"), align="L")
        self.ln(1)
        self.set_draw_color(*_COL_BORDER)
        self.line(_M, self.get_y(), self.w - _M, self.get_y())
        self.ln(5)
        self.set_text_color(*_COL_BODY)

    def footer(self):
        self.set_y(-12)
        self.set_font(self._family, "", 8)
        self.set_text_color(*_COL_MUTED)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def _section(pdf: _PDF, title: str) -> None:
    pdf.set_font(pdf._family, "B", 12)
    pdf.set_text_color(*_COL_SECTION_FG)
    pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*_COL_BODY)
    pdf.set_draw_color(*_COL_BORDER)
    pdf.line(_M, pdf.get_y(), pdf.w - _M, pdf.get_y())
    pdf.ln(3)


def _draw_table(
    pdf: _PDF,
    headers: list[str],
    rows: list[list],
    col_widths: list[float],
    alignments: list[str],
    total_row_idx: int | None = None,
) -> None:
    pdf.set_font(pdf._family, "B", 9)
    pdf.set_fill_color(*_COL_HEADER_BG)
    pdf.set_text_color(*_COL_HEADER_FG)
    pdf.set_draw_color(*_COL_BORDER)
    for h, w, a in zip(headers, col_widths, alignments):
        pdf.cell(w, _HEAD_H, h, border=1, fill=True, align=a)
    pdf.ln()

    pdf.set_text_color(*_COL_BODY)
    for ri, row in enumerate(rows):
        is_total = (total_row_idx is not None and ri == total_row_idx)
        pdf.set_font(pdf._family, "B" if is_total else "", 9)
        pdf.set_fill_color(*(_COL_TOTAL_BG if is_total else
                             _COL_ALT_BG   if ri % 2 == 0 else
                             _COL_WHITE))
        for val, w, a in zip(row, col_widths, alignments):
            pdf.cell(w, _ROW_H, pdf._f(str(val)), border=1, fill=True, align=a)
        pdf.ln()
    pdf.ln(4)


def _totals_table_data(totals_df: pd.DataFrame):
    body = totals_df.drop(index="TOTAL", errors="ignore")
    rows = []
    for _, r in body.iterrows():
        rows.append([
            str(r["Performance Date"]),
            str(int(r["Transactions"])),
            f"€{r['Gross (€)']:,.2f}",
            f"€{r['Fees (€)']:,.2f}",
            f"€{r['Net (€)']:,.2f}",
        ])
    total_idx = None
    if "TOTAL" in totals_df.index:
        tr = totals_df.loc["TOTAL"]
        rows.append([
            str(tr["Performance Date"]),
            str(int(tr["Transactions"])),
            f"€{tr['Gross (€)']:,.2f}",
            f"€{tr['Fees (€)']:,.2f}",
            f"€{tr['Net (€)']:,.2f}",
        ])
        total_idx = len(rows) - 1
    return rows, total_idx


def _stats_table_data(stats_df: pd.DataFrame, cat_cols: list[str]):
    body = stats_df.drop(index="TOTAL", errors="ignore")
    rows = []
    for _, r in body.iterrows():
        rows.append([str(r["Performance Date"]), str(int(r["Total Tickets"]))]
                    + [str(int(r[c])) for c in cat_cols])
    total_idx = None
    if "TOTAL" in stats_df.index:
        tr = stats_df.loc["TOTAL"]
        rows.append([str(tr["Performance Date"]), str(int(tr["Total Tickets"]))]
                    + [str(int(tr[c])) for c in cat_cols])
        total_idx = len(rows) - 1
    return rows, total_idx


def _pie_png(show_df: pd.DataFrame) -> bytes | None:
    try:
        import plotly.graph_objects as go
        if "category" not in show_df.columns:
            return None
        by_cat = (show_df.groupby("category", as_index=False)
                  .agg(tickets=("quantity", "sum"))
                  .sort_values("tickets", ascending=False))
        if by_cat.empty:
            return None
        n      = len(by_cat)
        colors = (_CHART_COLORS * ((n + len(_CHART_COLORS) - 1) // len(_CHART_COLORS)))[:n]
        fig    = go.Figure(data=[go.Pie(
            labels=by_cat["category"],
            values=by_cat["tickets"],
            marker=dict(colors=colors),
            hole=0.25,
            textinfo="label+percent+value",
            textfont=dict(size=12),
        )])
        fig.update_layout(
            width=700, height=480,
            paper_bgcolor="white",
            margin=dict(l=20, r=20, t=20, b=20),
            font=dict(family="Arial, Helvetica, sans-serif", size=12),
            legend=dict(orientation="v", x=1.0, y=0.5),
        )
        return fig.to_image(format="png", scale=2, engine="kaleido")
    except Exception:
        return None


def _trend_png(show_df: pd.DataFrame) -> bytes | None:
    try:
        import plotly.graph_objects as go
        if "date" not in show_df.columns or not show_df["date"].notna().any():
            return None
        ts = (show_df.dropna(subset=["date"])
              .assign(day=lambda d: d["date"].dt.normalize())
              .groupby("day", as_index=False)
              .agg(tickets=("quantity", "sum"))
              .sort_values("day"))
        if ts.empty:
            return None
        ts["day_number"] = (ts["day"] - ts["day"].min()).dt.days
        ts["cumulative"] = ts["tickets"].cumsum()
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=ts["day_number"],
            y=ts["cumulative"],
            mode="lines+markers",
            name="Cumulative tickets",
            line=dict(color=_CHART_COLORS[0], width=2),
            marker=dict(size=6, color=_CHART_COLORS[0]),
            fill="tozeroy",
            fillcolor="rgba(68,114,196,0.15)",
        ))
        fig.update_layout(
            title="Cumulative ticket sales",
            xaxis_title="Days since first sale",
            yaxis_title="Total tickets sold",
            xaxis=dict(dtick=1, tickmode="linear"),
            width=1400, height=420,
            paper_bgcolor="white", plot_bgcolor="white",
            margin=dict(l=60, r=40, t=55, b=60),
            font=dict(family="Arial, Helvetica, sans-serif", size=12),
        )
        return fig.to_image(format="png", scale=2, engine="kaleido")
    except Exception:
        return None


def _chart_png(stats_df: pd.DataFrame, cat_cols: list[str]) -> bytes | None:
    try:
        import plotly.graph_objects as go
        plot_df = stats_df.drop(index="TOTAL", errors="ignore").copy()
        fig = go.Figure()
        for i, cat in enumerate(cat_cols):
            fig.add_trace(go.Bar(
                name=cat,
                x=plot_df["Performance Date"].astype(str),
                y=plot_df[cat],
                marker_color=_CHART_COLORS[i % len(_CHART_COLORS)],
            ))
        fig.update_layout(
            barmode="stack",
            title="Ticket categories per night",
            xaxis_title="Performance Date",
            yaxis_title="Tickets",
            legend_title="Category",
            width=1400, height=420,
            paper_bgcolor="white", plot_bgcolor="white",
            margin=dict(l=50, r=160, t=55, b=80),
            font=dict(family="Arial, Helvetica, sans-serif", size=12),
        )
        return fig.to_image(format="png", scale=2, engine="kaleido")
    except Exception:
        return None


def _metric_strip(pdf: _PDF, pairs: list[tuple[str, str]], fill: tuple) -> None:
    cell_w = _CW / len(pairs)
    pdf.set_fill_color(*fill)
    pdf.set_draw_color(*_COL_BORDER)
    for label, value in pairs:
        x0, y0 = pdf.get_x(), pdf.get_y()
        pdf.set_font(pdf._family, "", 8)
        pdf.set_text_color(*_COL_MUTED)
        pdf.cell(cell_w, 5, label, border=1, fill=True, align="C")
        pdf.ln()
        pdf.set_x(x0)
        pdf.set_font(pdf._family, "B", 11)
        pdf.set_text_color(*_COL_BODY)
        pdf.cell(cell_w, 8, pdf._f(value), border=1, fill=True, align="C")
        pdf.set_xy(x0 + cell_w, y0)
    pdf.ln(13)
    pdf.ln(3)


def build_reconciliation_pdf(
    show: str,
    pp_start: date,
    pp_end: date,
    totals_df: pd.DataFrame,
    stats_df: pd.DataFrame,
    show_txns: list[dict],
    tt_gross: float | None = None,
    pp_gross: float | None = None,
    show_df: pd.DataFrame | None = None,
    capacity: int = 0,
) -> bytes:
    pdf = _PDF(show, "Helvetica")  # placeholder; overridden after font registration
    family = _register_fonts(pdf)
    pdf._family = family

    pdf.add_page()

    # Title block
    pdf.set_font(family, "B", 18)
    pdf.set_text_color(*_COL_BODY)
    pdf.cell(0, 10, "Reconciliation Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(family, "", 10)
    pdf.set_text_color(*_COL_MUTED)
    pdf.cell(0, 6, f"Production: {show}",                                          new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, pdf._f(f"Date range: {pp_start}  →  {pp_end}"),    new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%d %b %Y  %H:%M')}",    new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # PayPal summary strip
    if show_txns:
        gross = sum(t["gross"] for t in show_txns)
        fees  = sum(t["fee"]   for t in show_txns)
        net   = sum(t["net"]   for t in show_txns)
        _metric_strip(pdf, [
            ("Transactions", str(len(show_txns))),
            ("Gross",  f"€{gross:,.2f}"),
            ("Fees",   f"€{fees:,.2f}"),
            ("Net",    f"€{net:,.2f}"),
        ], _COL_ALT_BG)

    # Totals table
    _section(pdf, "Totals")
    if not totals_df.empty:
        rows, total_idx = _totals_table_data(totals_df)
        _draw_table(pdf,
                    headers=["Performance Date", "Txns", "Gross (€)", "Fees (€)", "Net (€)"],
                    rows=rows,
                    col_widths=[97.0, 22.0, 50.0, 49.0, 49.0],
                    alignments=["L", "R", "R", "R", "R"],
                    total_row_idx=total_idx)
    else:
        pdf.set_font(family, "I", 9)
        pdf.set_text_color(*_COL_MUTED)
        pdf.cell(0, 8, "No performance date data available.", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*_COL_BODY)
        pdf.ln(4)

    # Statistics table + chart
    pdf.add_page()
    _section(pdf, "Statistics")
    cat_cols = [c for c in stats_df.columns if c not in ("Performance Date", "Total Tickets")]

    if not stats_df.empty and cat_cols:
        date_w  = 75.0
        total_w = 25.0
        cat_w   = round((_CW - date_w - total_w) / len(cat_cols), 1)
        rows, total_idx = _stats_table_data(stats_df, cat_cols)
        _draw_table(pdf,
                    headers=["Performance Date", "Total"] + cat_cols,
                    rows=rows,
                    col_widths=[date_w, total_w] + [cat_w] * len(cat_cols),
                    alignments=["L", "R"] + ["R"] * len(cat_cols),
                    total_row_idx=total_idx)

        png = _chart_png(stats_df, cat_cols)
        if png:
            if pdf.get_y() > pdf.h - 100:
                pdf.add_page()
            pdf.image(io.BytesIO(png), x=_M, w=_CW)
            pdf.ln(4)
    else:
        pdf.set_font(family, "I", 9)
        pdf.set_text_color(*_COL_MUTED)
        pdf.cell(0, 8, "No category or performance date data available.", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*_COL_BODY)
        pdf.ln(4)

    # ── Analytics pages (only when show_df provided) ─────────────────────────
    if show_df is not None and not show_df.empty:
        pdf.add_page()

        # Left column: category pie chart
        # Right column: yield & capacity metrics
        pie_w   = 125.0
        right_x = _M + pie_w + 7

        _section(pdf, "Ticket Category Breakdown")
        y_top = pdf.get_y()

        pie_png = _pie_png(show_df)
        if pie_png:
            pdf.image(io.BytesIO(pie_png), x=_M, y=y_top, w=pie_w)

        # Yield block in right column, aligned to same y_top
        pdf.set_xy(right_x, y_top)
        right_w = _CW - pie_w - 7

        def _right_cell(label: str, value: str, fill: tuple, bold: bool = False) -> None:
            pdf.set_fill_color(*fill)
            pdf.set_draw_color(*_COL_BORDER)
            pdf.set_font(family, "", 8)
            pdf.set_text_color(*_COL_MUTED)
            pdf.cell(right_w, 5, label, border=1, fill=True, align="C",
                     new_x="LEFT", new_y="NEXT")
            pdf.set_font(family, "B" if bold else "", 11)
            pdf.set_text_color(*_COL_BODY)
            pdf.cell(right_w, 8, pdf._f(value), border=1, fill=True, align="C",
                     new_x="LEFT", new_y="NEXT")
            pdf.set_xy(right_x, pdf.get_y() + 1)

        total_tickets = int(show_df["quantity"].sum()) if "quantity" in show_df.columns else 0
        total_revenue = show_df["revenue"].sum() if "revenue" in show_df.columns else 0.0

        pdf.set_xy(right_x, y_top)
        pdf.set_font(family, "B", 11)
        pdf.set_text_color(*_COL_SECTION_FG)
        pdf.cell(right_w, 8, "Yield & Capacity", new_x="LEFT", new_y="NEXT")
        pdf.set_draw_color(*_COL_BORDER)
        pdf.line(right_x, pdf.get_y(), right_x + right_w, pdf.get_y())
        pdf.set_xy(right_x, pdf.get_y() + 4)
        pdf.set_text_color(*_COL_BODY)

        _right_cell("Total Tickets Sold", str(total_tickets), _COL_ALT_BG)
        _right_cell("Total Revenue",      f"€{total_revenue:,.2f}", _COL_WHITE)

        if capacity > 0:
            sell_through = total_tickets / capacity * 100
            rev_per_seat = total_revenue / capacity
            _right_cell("Capacity",       str(capacity),            _COL_ALT_BG)
            _right_cell("Sell-through",   f"{sell_through:.1f}%",   _COL_WHITE, bold=True)
            _right_cell("Revenue / Seat", f"€{rev_per_seat:.2f}",   _COL_ALT_BG)

            # Capacity fill bar spanning the right column
            bar_y = pdf.get_y() + 3
            bar_h = 9
            fill_w = right_w * min(sell_through, 100.0) / 100.0
            bar_color = (70, 140, 70) if sell_through >= 95 else (70, 130, 180)
            pdf.set_fill_color(210, 210, 210)
            pdf.set_draw_color(*_COL_BORDER)
            pdf.rect(right_x, bar_y, right_w, bar_h, "FD")
            pdf.set_fill_color(*bar_color)
            pdf.rect(right_x, bar_y, fill_w, bar_h, "F")
            pdf.set_xy(right_x, bar_y)
            pdf.set_font(family, "B", 8)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(right_w, bar_h,
                     f"{sell_through:.1f}% sold  ({total_tickets} / {capacity} seats)",
                     align="C")
            pdf.set_text_color(*_COL_BODY)

        # Advance past the pie chart height before the next section
        pie_bottom = y_top + (pie_w * 480 / 700)  # derived from 700×480px aspect ratio
        if pdf.get_y() < pie_bottom:
            pdf.set_y(pie_bottom)
        pdf.ln(6)

        # Sales trend — full width (start a new page if little room remains)
        if pdf.get_y() > pdf.h - 110:
            pdf.add_page()
        _section(pdf, "Sales Trend")
        trend_png = _trend_png(show_df)
        if trend_png:
            if pdf.get_y() > pdf.h - 90:
                pdf.add_page()
            pdf.image(io.BytesIO(trend_png), x=_M, w=_CW)
            pdf.ln(4)
        else:
            pdf.set_font(family, "", 9)
            pdf.set_text_color(*_COL_MUTED)
            pdf.cell(0, 8, "No sale-date data available for trend chart.",
                     new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*_COL_BODY)
            pdf.ln(4)

        # Trend summary stats table (mirrors the analytics tab)
        if "date" in show_df.columns and show_df["date"].notna().any():
            ts = (show_df.dropna(subset=["date"])
                  .assign(day=lambda d: d["date"].dt.normalize())
                  .groupby("day", as_index=False)
                  .agg(tickets=("quantity", "sum"))
                  .sort_values("day"))
            if not ts.empty:
                ts["day_number"] = (ts["day"] - ts["day"].min()).dt.days
                peak = ts.loc[ts["tickets"].idxmax()]
                _draw_table(pdf,
                    headers=["First Sale", "Last Sale", "Selling Window",
                             "Peak Day", "Peak Tickets"],
                    rows=[[
                        str(ts["day"].min().date()),
                        str(ts["day"].max().date()),
                        f"{int(ts['day_number'].max()) + 1} days",
                        f"Day {int(peak['day_number'])}  ({peak['day'].date()})",
                        str(int(peak["tickets"])),
                    ]],
                    col_widths=[48.0, 48.0, 36.0, 85.0, 50.0],
                    alignments=["L", "L", "R", "L", "R"],
                )

    # PayPal Reconciliation Check — always last
    if tt_gross is not None and pp_gross is not None:
        if pdf.get_y() > pdf.h - 80:
            pdf.add_page()
        _section(pdf, "PayPal Reconciliation Check")
        diff   = round(pp_gross - tt_gross, 2)
        passed = abs(diff) < 0.02
        _metric_strip(pdf, [
            ("Ticket Tailor Gross", f"€{tt_gross:,.2f}"),
            ("PayPal Gross",        f"€{pp_gross:,.2f}"),
            ("Difference",          f"€{diff:,.2f}"),
        ], _COL_PASS_BG if passed else _COL_FAIL_BG)
        status = ("Reconciliation passed — values match." if passed else
                  f"Difference of €{diff:.2f}. Check for refunds or transactions outside the date window.")
        pdf.set_font(family, "B" if passed else "", 9)
        pdf.set_text_color(0, 100, 0) if passed else pdf.set_text_color(160, 60, 0)
        pdf.multi_cell(0, 6, pdf._f(status))
        pdf.set_text_color(*_COL_BODY)

    return bytes(pdf.output())
