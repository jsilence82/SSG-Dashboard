"""PDF export for the reconciliation report."""

import io
import os
from datetime import date, datetime

import pandas as pd
from fpdf import FPDF

_M       = 15    # page margin mm
_CW      = 180   # content width mm
_ROW_H   = 6     # table row height mm
_HEAD_H  = 7     # header row height mm

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
        super().__init__()
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


def _chart_png(stats_df: pd.DataFrame, cat_cols: list[str]) -> bytes | None:
    try:
        import plotly.express as px
        plot_df = stats_df.drop(index="TOTAL", errors="ignore").copy()
        fig = px.bar(
            plot_df, x="Performance Date", y=cat_cols, barmode="stack",
            title="Ticket categories per night",
            labels={"value": "Tickets", "variable": "Category"},
        )
        fig.update_layout(
            width=900, height=420,
            paper_bgcolor="white", plot_bgcolor="white",
            margin=dict(l=40, r=20, t=50, b=80),
            font=dict(family="Arial, Helvetica, sans-serif", size=11),
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
    pdf.cell(0, 6, pdf._f(f"PayPal date range: {pp_start}  →  {pp_end}"),    new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%d %b %Y  %H:%M')}",    new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # PayPal summary strip
    if show_txns:
        gross = sum(t["gross"] for t in show_txns)
        fees  = sum(t["fee"]   for t in show_txns)
        net   = sum(t["net"]   for t in show_txns)
        _metric_strip(pdf, [
            ("Transactions", str(len(show_txns))),
            ("PayPal Gross",  f"€{gross:,.2f}"),
            ("PayPal Fees",   f"€{fees:,.2f}"),
            ("PayPal Net",    f"€{net:,.2f}"),
        ], _COL_ALT_BG)

    # Totals table
    _section(pdf, "Totals")
    if not totals_df.empty:
        rows, total_idx = _totals_table_data(totals_df)
        _draw_table(pdf,
                    headers=["Performance Date", "Txns", "Gross (€)", "Fees (€)", "Net (€)"],
                    rows=rows,
                    col_widths=[65.0, 20.0, 33.0, 31.0, 31.0],
                    alignments=["L", "R", "R", "R", "R"],
                    total_row_idx=total_idx)
    else:
        pdf.set_font(family, "I", 9)
        pdf.set_text_color(*_COL_MUTED)
        pdf.cell(0, 8, "No performance date data available.", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*_COL_BODY)
        pdf.ln(4)

    # Statistics table + chart
    _section(pdf, "Statistics")
    cat_cols = [c for c in stats_df.columns if c not in ("Performance Date", "Total Tickets")]

    if not stats_df.empty and cat_cols:
        date_w  = 55.0
        total_w = 22.0
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
            if pdf.get_y() > 200:
                pdf.add_page()
            pdf.image(io.BytesIO(png), x=_M, w=_CW)
            pdf.ln(4)
    else:
        pdf.set_font(family, "I", 9)
        pdf.set_text_color(*_COL_MUTED)
        pdf.cell(0, 8, "No category or performance date data available.", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*_COL_BODY)
        pdf.ln(4)

    # Reconciliation check
    if tt_gross is not None and pp_gross is not None:
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
