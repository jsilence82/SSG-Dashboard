"""Internationalisation: English / German string lookup."""

import streamlit as st

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # ── App-level ───────────────────────────────────────────────────────
        "app_title":              "🎭 SSG Ticket Sales Dashboard",

        # ── Top-level tabs ──────────────────────────────────────────────────
        "tab_analytics":          "📊 Analytics",
        "tab_reconciliation":     "🧾 Reconciliation Report",
        "tab_settings":           "⚙️ Settings",

        # ── Analytics sub-tabs ──────────────────────────────────────────────
        "tab_overview":           "📊 Overview",
        "tab_per_show":           "🥧 Per-show breakdown",
        "tab_ranking":            "🏆 Show ranking",
        "tab_categories":         "🎟 Categories",
        "tab_trend":              "📈 Sales trend",
        "tab_yield":              "💺 Yield & Capacity",
        "tab_repeat":             "🔄 Repeat buyers",
        "tab_multi":              "🌙 Multi-night",
        "tab_detail":             "📋 Detail table",

        # ── Dashboard / filters ─────────────────────────────────────────────
        "filters":                "Filters",
        "shows_to_include":       "Shows to include",
        "statuses":               "Statuses",
        "no_rows_match":          "No rows match the current filters.",

        # ── Analytics section headers (passed via render_dashboard) ─────────
        "ticket_categories":      "Ticket categories",
        "sales_over_time":        "Sales over time",
        "yield_capacity":         "Yield & Capacity",
        "audience_retention":     "Audience Retention",
        "multi_night_analysis":   "Multi-night Analysis",
        "detail_table":           "Detail table",

        # ── KPIs ────────────────────────────────────────────────────────────
        "kpi_total_tickets":      "Total tickets sold",
        "kpi_total_revenue":      "Total revenue",
        "kpi_shows":              "Shows",
        "kpi_avg_tickets":        "Avg tickets / show",
        "kpi_avg_revenue":        "Avg revenue / ticket",

        # ── Overview ────────────────────────────────────────────────────────
        "tickets_sold_per_show":  "Tickets sold per show",
        "revenue_per_show":       "Revenue per show",
        "show_label":             "Show",
        "tickets_label":          "Tickets",
        "revenue_label":          "Revenue (€)",

        # ── Ranking ─────────────────────────────────────────────────────────
        "filter_by_category":     "Filter by category (blank = all)",
        "rank_by":                "Rank by",
        "rank_tickets":           "Tickets sold",
        "rank_revenue":           "Revenue",

        # ── Categories ──────────────────────────────────────────────────────
        "ticket_share_by_cat":    "Overall share of tickets by category",
        "category_mix_per_show":  "Category mix per show",
        "quantity_label":         "Tickets",
        "category_label":         "Category",

        # ── Sales trend ─────────────────────────────────────────────────────
        "shows_displayed":        "**Shows displayed**",
        "select_at_least_one":    "Select at least one show.",
        "view_cumulative":        "Cumulative",
        "view_daily":             "Daily",
        "total_tickets_y":        "Total tickets sold",
        "daily_tickets_y":        "Tickets sold",
        "no_valid_dates":         "No valid dates in this dataset.",
        "day_number_x":           "Days since first sale",
        "first_sale_col":         "First sale",
        "last_sale_col":          "Last sale",
        "selling_window_col":     "Selling window",
        "peak_day_col":           "Peak day",
        "peak_tickets_col":       "Peak tickets",
        "days_suffix":            "days",
        "day_prefix":             "Day",

        # ── Yield & Capacity ────────────────────────────────────────────────
        "capacity_per_show":      "**Capacity per show** — enter total seats available. Values are saved and pre-filled from the API when available.",
        "save_capacities":        "💾 Save capacities",
        "capacities_saved":       "Capacities saved.",
        "ticket_sale_window":     "**Ticket sale window per show** — from when tickets went on sale to when the event ended. Pre-filled from Ticket Tailor's event series when available.",
        "on_sale_from":           "on sale from",
        "event_ended":            "event ended",
        "save_perf_dates":        "💾 Save performance dates",
        "perf_dates_saved":       "Performance dates saved.",
        "enter_capacity":         "Enter capacity above to unlock yield metrics.",
        "sell_through_rate":      "Sell-through rate (%)",
        "rev_per_seat_title":     "Revenue per available seat (€)",
        "full_house":             "Full house",
        "percent_label":          "%",
        "seat_label":             "€ / seat",

        # ── Repeat buyers ───────────────────────────────────────────────────
        "map_buyer_column":       "Map a buyer email or name column to enable audience retention analysis.",
        "no_buyer_ids":           "No valid buyer identifiers found in the data.",
        "unique_buyers":          "Unique buyers",
        "repeat_buyers_2plus":    "Repeat buyers (2+)",
        "loyal_buyers_3plus":     "Loyal buyers (3+)",
        "shows_attended_title":   "Number of shows attended per buyer",
        "shows_attended_x":       "Shows attended",
        "buyers_label":           "Buyers",
        "single_show_buyers":     "Single-show buyers",
        "repeat_buyers_label":    "Repeat buyers",
        "single_vs_repeat":       "Single-show vs repeat buyers per show",

        # ── Multi-night ─────────────────────────────────────────────────────
        "nights_by_dow":          "### Nights by day of week — all shows",
        "tickets_by_dow":         "Tickets sold by day of week",
        "revenue_by_dow":         "Revenue by day of week",
        "tickets_by_dow_per_show":"Tickets by day of week, per show",
        "day_label":              "Day",
        "night_label":            "Night",
        "select_show":            "Select show",
        "sales_velocity":         "**Sales velocity — which night sold fastest?**",
        "no_multi_shows":         "No shows with multiple nights found in the current data.",
        "no_occ_data":            "Map an occurrence ID or performance date column to enable multi-night analysis. In Ticket Tailor data, occurrence maps to the `event_id` field.",
        "night_prefix":           "Night",
        "cumulative_per_night":   "cumulative sales per night (Day 0 = first sale per night)",
        "cumulative_label":       "Tickets sold",
        "tickets_per_night":      "tickets per night",
        "revenue_per_night":      "revenue per night",

        # ── Detail table ────────────────────────────────────────────────────
        "csv_download":           "⬇ CSV",
        "excel_download":         "⬇ Excel",

        # ── Sidebar ─────────────────────────────────────────────────────────
        "sidebar_load":           "📂 Load cache",
        "sidebar_refresh":        "🔄 Refresh",
        "sidebar_fetching":       "Fetching from Ticket Tailor…",
        "sidebar_no_key":         "Configure API key in ⚙️ Settings first.",

        # ── Settings ────────────────────────────────────────────────────────
        "settings_language_header": "🌐 Language",
        "language_label":           "Display language",
        "language_saved":           "Language saved.",

        # ── Reconciliation — UI ──────────────────────────────────────────────
        "recon_title":            "🧾 Reconciliation Report",
        "recon_desc":             "Generates **Totals** and **Statistics** tables for a selected production, cross-referenced with PayPal transaction data where available.",
        "production_to_report":   "Production to report",
        "pp_search_from":         "PayPal search from",
        "pp_search_to":           "PayPal search to",
        "generate_report":        "📊 Generate Report",
        "force_refresh":          "🔄 Force refresh from API and Generate",
        "matched_transactions":   "Matched transactions",
        "gross":                  "Gross",
        "fees":                   "Fees",
        "net":                    "Net",
        "totals_header":          "### 💰 Totals — {show}",
        "stats_header":           "### 🎟 Statistics — {show}",
        "recon_check":            "### ✅ PayPal Reconciliation Check",
        "tt_gross_label":         "Ticket Tailor gross",
        "pp_gross_label":         "PayPal gross",
        "difference_label":       "Difference",
        "recon_passed":           "✓ Values match — reconciliation passed.",
        "recon_diff_warning":     "⚠️ Difference of €{diff:.2f}. Check for refunds, fees, or transactions outside the date window.",
        "no_perf_date_data":      "No performance date data found. Ensure the **performance_date** column is mapped and tickets have dates.",
        "no_category_data":       "No category or performance date data available for the Statistics table.",
        "unmatched_header":       "**PayPal transactions with no matching Ticket Tailor entry:**",
        "totals_sub":             "**Totals**",
        "operator_excluded":      "Revenue excluded from Ticket Tailor gross (operator-only — box-office sales never processed through PayPal):",
        "pdf_download":           "⬇️ Download PDF Report",
        "pdf_failed":             "PDF generation failed: {exc}",
        "paypal_connected":       "✓ PayPal connected · {env} (token active for this session)",
        "paypal_no_token":        "💡 PayPal credentials configured but no active token — go to ⚙️ Settings to connect.",
        "paypal_not_configured":  "💡 PayPal not configured — go to ⚙️ Settings to add credentials and connect.",
        "cache_covers":           "✓ Cache covers this date range — no API call needed.  \n📦 {label}",
        "cache_partial":          "📦 Cache: {label}  \n⬇️ Will fetch missing portion(s): {parts}",
        "no_pp_cache":            "📭 No PayPal cache yet — first load will fetch from the API and save locally.",
        "loaded_from_cache":      "Loaded {n} transactions from cache.",
        "connect_paypal_first":   "Connect to PayPal first using 'Test & get token' above.",
        "loaded_transactions":    "Loaded {n} transactions for date range ({env}).",
        "load_failed":            "Load failed ({env}): {exc}",
        "refreshed":              "Refreshed — {n} transactions ({env}).",
        "refresh_failed":         "Refresh failed ({env}): {exc}",
        "no_pp_creds":            "No PayPal credentials saved — configure them in ⚙️ Settings.",
        "connecting_paypal":      "Connecting to PayPal…",
        "could_not_get_token":    "Could not obtain PayPal token: {result}",
        "tickets_per_category":   "Ticket categories per night",
        "building_pdf":           "Building PDF…",

        # ── Reconciliation — DataFrame column display names ──────────────────
        "col_performance_date":   "Performance Date",
        "col_transactions":       "Transactions",
        "col_gross":              "Gross (€)",
        "col_fees":               "Fees (€)",
        "col_net":                "Net (€)",
        "col_total_tickets":      "Total Tickets",
        "col_total_label":        "Transactions Total",
        "col_stats_total":        "Total",

        # ── PDF — section headers ────────────────────────────────────────────
        "pdf_header":             "SSG Ticket Sales Dashboard",
        "pdf_page":               "Page {n}",
        "pdf_production":         "Production: {show}",
        "pdf_period":             "Period: {start}  →  {end}",
        "pdf_generated":          "Generated: {date}",
        "pdf_enter_values":       "Please enter the following values in your accounts",
        "pdf_totals_section":     "Totals",
        "pdf_stats_section":      "Statistics",
        "pdf_categories_section": "Ticket Categories",
        "pdf_yield_section":      "Yield & Capacity",
        "pdf_revenue_trend":      "Revenue Trend",
        "pdf_no_perf_data":       "No performance date data available.",
        "pdf_no_cat_data":        "No category or performance date data available.",
        "pdf_no_sales_data":      "No sales data available for trend chart.",
        "pdf_total_tickets_sold": "Total Tickets Sold",
        "pdf_total_revenue":      "Total Revenue",
        "pdf_capacity":           "Capacity",
        "pdf_sell_through":       "Sell-through",
        "pdf_rev_per_seat":       "Revenue / Seat",
        "pdf_seats_suffix":       "seats",
        "pdf_sold_label":         "sold",
        "pdf_pie_title":          "Ticket Category Breakdown",
        "pdf_trend_title":        "Cumulative ticket sales",
        "pdf_trend_x":            "Days since first sale",
        "pdf_trend_y":            "Total tickets sold",
        "pdf_daily_title":        "Daily ticket sales",
        "pdf_daily_x":            "Date",
        "pdf_daily_y":            "Tickets sold",
        "pdf_chart_title":        "Ticket categories per night",
        "pdf_chart_x":            "Performance Date",
        "pdf_chart_legend":       "Category",
        "pdf_first_sale":         "First sale",
        "pdf_last_sale":          "Last sale",
        "pdf_selling_window":     "Selling window",
        "pdf_peak_day":           "Peak day",
        "pdf_peak_tickets":       "Peak tickets",
        "pdf_days_suffix":        "days",
        "pdf_day_prefix":         "Day",
        "pdf_recon_section":      "Ticket Tailor / PayPal Reconciliation",
        "pdf_tt_gross":           "Ticket Tailor Gross",
        "pdf_pp_gross":           "PayPal Gross",
        "pdf_diff":               "Difference",
        "pdf_recon_passed":       "Reconciliation passed — values match.",
        "pdf_recon_diff":         "Difference of {diff:.2f} €. Check for refunds or transactions outside the date window.",
    },

    "de": {
        # ── App-level ───────────────────────────────────────────────────────
        "app_title":              "🎭 SSG Online Ticketverkauf",

        # ── Top-level tabs ──────────────────────────────────────────────────
        "tab_analytics":          "📊 Analyse",
        "tab_reconciliation":     "🧾 Kassenabschluss",
        "tab_settings":           "⚙️ Einstellungen",

        # ── Analytics sub-tabs ──────────────────────────────────────────────
        "tab_overview":           "📊 Übersicht",
        "tab_per_show":           "🥧 Aufführungsübersicht",
        "tab_ranking":            "🏆 Rangliste",
        "tab_categories":         "🎟 Kategorien",
        "tab_trend":              "📈 Verkaufstrend",
        "tab_yield":              "💺 Ertrag & Kapazität",
        "tab_repeat":             "🔄 Stammkäufer",
        "tab_multi":              "🌙 Mehrabend-Analyse",
        "tab_detail":             "📋 Detailtabelle",

        # ── Dashboard / filters ─────────────────────────────────────────────
        "filters":                "Filter",
        "shows_to_include":       "Aufführungen einbeziehen",
        "statuses":               "Status",
        "no_rows_match":          "Keine Zeilen entsprechen den aktuellen Filtern.",

        # ── Analytics section headers ────────────────────────────────────────
        "ticket_categories":      "Ticketkategorien",
        "sales_over_time":        "Umsatz über Zeit",
        "yield_capacity":         "Ertrag & Kapazität",
        "audience_retention":     "Publikumstreue",
        "multi_night_analysis":   "Mehrabend-Analyse",
        "detail_table":           "Detailtabelle",

        # ── KPIs ────────────────────────────────────────────────────────────
        "kpi_total_tickets":      "Verkaufte Tickets gesamt",
        "kpi_total_revenue":      "Gesamtumsatz",
        "kpi_shows":              "Aufführungen",
        "kpi_avg_tickets":        "Ø Tickets / Aufführung",
        "kpi_avg_revenue":        "Ø Umsatz / Ticket",

        # ── Overview ────────────────────────────────────────────────────────
        "tickets_sold_per_show":  "Verkaufte Tickets pro Aufführung",
        "revenue_per_show":       "Umsatz pro Aufführung",
        "show_label":             "Aufführung",
        "tickets_label":          "Tickets",
        "revenue_label":          "Umsatz (€)",

        # ── Ranking ─────────────────────────────────────────────────────────
        "filter_by_category":     "Nach Kategorie filtern (leer = alle)",
        "rank_by":                "Sortieren nach",
        "rank_tickets":           "Verkaufte Tickets",
        "rank_revenue":           "Umsatz",

        # ── Categories ──────────────────────────────────────────────────────
        "ticket_share_by_cat":    "Gesamtanteil der Tickets nach Kategorie",
        "category_mix_per_show":  "Kategoriemix pro Aufführung",
        "quantity_label":         "Tickets",
        "category_label":         "Kategorie",

        # ── Sales trend ─────────────────────────────────────────────────────
        "shows_displayed":        "**Angezeigte Aufführungen**",
        "select_at_least_one":    "Mindestens eine Aufführung auswählen.",
        "view_cumulative":        "Kumulativ",
        "view_daily":             "Täglich",
        "total_tickets_y":        "Gesamtzahl der verkauften Tickets",
        "daily_tickets_y":        "Verkaufte Tickets",
        "no_valid_dates":         "Keine gültigen Datumsangaben in diesem Datensatz.",
        "day_number_x":           "Tage seit erstem Verkauf",
        "first_sale_col":         "Erster Verkauf",
        "last_sale_col":          "Letzter Verkauf",
        "selling_window_col":     "Verkaufszeitraum",
        "peak_day_col":           "Höchster Tag",
        "peak_tickets_col":       "Höchste Ticketanzahl",
        "days_suffix":            "Tage",
        "day_prefix":             "Tag",

        # ── Yield & Capacity ────────────────────────────────────────────────
        "capacity_per_show":      "**Kapazität pro Aufführung** — Gesamtzahl der verfügbaren Sitzplätze eingeben. Werte werden gespeichert und automatisch aus der API befüllt.",
        "save_capacities":        "💾 Kapazitäten speichern",
        "capacities_saved":       "Kapazitäten gespeichert.",
        "ticket_sale_window":     "**Ticketverkaufszeitraum pro Aufführung** — von Beginn des Vorverkaufs bis zum Ende der Veranstaltung. Wird automatisch aus dem Ticket Tailor Eventseries befüllt.",
        "on_sale_from":           "Vorverkauf ab",
        "event_ended":            "Veranstaltung beendet",
        "save_perf_dates":        "💾 Aufführungsdaten speichern",
        "perf_dates_saved":       "Aufführungsdaten gespeichert.",
        "enter_capacity":         "Kapazität oben eingeben, um Ertragsmetriken freizuschalten.",
        "sell_through_rate":      "Auslastungsgrad (%)",
        "rev_per_seat_title":     "Umsatz pro verfügbarem Sitzplatz (€)",
        "full_house":             "Ausverkauft",
        "percent_label":          "%",
        "seat_label":             "€ / Sitz",

        # ── Repeat buyers ───────────────────────────────────────────────────
        "map_buyer_column":       "Käufer-E-Mail oder Namensspalte zuordnen, um die Publikumstreue-Analyse zu aktivieren.",
        "no_buyer_ids":           "Keine gültigen Käufer-Identifikatoren in den Daten gefunden.",
        "unique_buyers":          "Eindeutige Käufer",
        "repeat_buyers_2plus":    "Stammkäufer (2+)",
        "loyal_buyers_3plus":     "Treue Käufer (3+)",
        "shows_attended_title":   "Anzahl der besuchten Aufführungen pro Käufer",
        "shows_attended_x":       "Besuchte Aufführungen",
        "buyers_label":           "Käufer",
        "single_show_buyers":     "Einmal-Käufer",
        "repeat_buyers_label":    "Stammkäufer",
        "single_vs_repeat":       "Einmal- vs. Stammkäufer pro Aufführung",

        # ── Multi-night ─────────────────────────────────────────────────────
        "nights_by_dow":          "### Abende nach Wochentag — alle Aufführungen",
        "tickets_by_dow":         "Verkaufte Tickets nach Wochentag",
        "revenue_by_dow":         "Umsatz nach Wochentag",
        "tickets_by_dow_per_show":"Tickets nach Wochentag, pro Aufführung",
        "day_label":              "Tag",
        "night_label":            "Abend",
        "select_show":            "Aufführung auswählen",
        "sales_velocity":         "**Verkaufsgeschwindigkeit — welcher Abend verkaufte am schnellsten?**",
        "no_multi_shows":         "Keine Aufführungen mit mehreren Abenden in den aktuellen Daten gefunden.",
        "no_occ_data":            "Occurrence-ID oder Aufführungsdatum zuordnen, um die Mehrabend-Analyse zu aktivieren. In Ticket Tailor-Daten entspricht die Occurrence der `event_id`.",
        "night_prefix":           "Abend",
        "cumulative_per_night":   "kumulative Verkäufe pro Abend (Tag 0 = erster Verkauf pro Abend)",
        "cumulative_label":       "Verkaufte Tickets",
        "tickets_per_night":      "Tickets pro Abend",
        "revenue_per_night":      "Umsatz pro Abend",

        # ── Detail table ────────────────────────────────────────────────────
        "csv_download":           "⬇ CSV",
        "excel_download":         "⬇ Excel",

        # ── Sidebar ─────────────────────────────────────────────────────────
        "sidebar_load":           "📂 Cache laden",
        "sidebar_refresh":        "🔄 Aktualisieren",
        "sidebar_fetching":       "Lade von Ticket Tailor…",
        "sidebar_no_key":         "Zuerst API-Schlüssel in ⚙️ Einstellungen konfigurieren.",

        # ── Settings ────────────────────────────────────────────────────────
        "settings_language_header": "🌐 Sprache",
        "language_label":           "Anzeigesprache",
        "language_saved":           "Sprache gespeichert.",

        # ── Reconciliation — UI ──────────────────────────────────────────────
        "recon_title":            "🧾 Kassenabschluss",
        "recon_desc":             "Erstellt **Gesamt-** und **Statistiktabellen** für eine ausgewählte Produktion, abgeglichen mit PayPal-Transaktionsdaten, sofern verfügbar.",
        "production_to_report":   "Produktion für den Bericht",
        "pp_search_from":         "PayPal-Suche von",
        "pp_search_to":           "PayPal-Suche bis",
        "generate_report":        "📊 Bericht erstellen",
        "force_refresh":          "🔄 Neu laden und Bericht erstellen",
        "matched_transactions":   "Zugeordnete Transaktionen",
        "gross":                  "Brutto",
        "fees":                   "Gebühren",
        "net":                    "Netto",
        "totals_header":          "### 💰 Gesamtbeträge — {show}",
        "stats_header":           "### 🎟 Statistik — {show}",
        "recon_check":            "### ✅ PayPal-Abgleich",
        "tt_gross_label":         "Ticket Tailor Brutto",
        "pp_gross_label":         "PayPal Brutto",
        "difference_label":       "Differenz",
        "recon_passed":           "✓ Werte stimmen überein — Abgleich erfolgreich.",
        "recon_diff_warning":     "⚠️ Differenz von €{diff:.2f}. Prüfen Sie Rückerstattungen, Gebühren oder Transaktionen außerhalb des Datumsfensters.",
        "no_perf_date_data":      "Keine Aufführungsdaten gefunden. Stellen Sie sicher, dass die Spalte **performance_date** zugeordnet ist und Tickets Daten haben.",
        "no_category_data":       "Keine Kategorie- oder Aufführungsdaten für die Statistiktabelle verfügbar.",
        "unmatched_header":       "**PayPal-Transaktionen ohne übereinstimmenden Ticket Tailor-Eintrag:**",
        "totals_sub":             "**Summen**",
        "operator_excluded":      "Aus dem Ticket Tailor-Bruttobetrag ausgeschlossener Umsatz (nur Kassenverkauf — nie über PayPal abgewickelt):",
        "pdf_download":           "⬇️ PDF-Bericht herunterladen",
        "pdf_failed":             "PDF-Erstellung fehlgeschlagen: {exc}",
        "paypal_connected":       "✓ PayPal verbunden · {env} (Token für diese Sitzung aktiv)",
        "paypal_no_token":        "💡 PayPal-Anmeldedaten konfiguriert, aber kein aktiver Token — gehe zu ⚙️ Einstellungen zum Verbinden.",
        "paypal_not_configured":  "💡 PayPal nicht konfiguriert — gehe zu ⚙️ Einstellungen, um Anmeldedaten hinzuzufügen.",
        "cache_covers":           "✓ Cache deckt diesen Datumsbereich ab — kein API-Aufruf erforderlich.  \n📦 {label}",
        "cache_partial":          "📦 Cache: {label}  \n⬇️ Fehlende Zeiträume werden abgerufen: {parts}",
        "no_pp_cache":            "📭 Noch kein PayPal-Cache — beim ersten Laden werden Daten von der API abgerufen.",
        "loaded_from_cache":      "{n} Transaktionen aus dem Cache geladen.",
        "connect_paypal_first":   "Bitte zuerst PayPal über 'Testen & Token abrufen' verbinden.",
        "loaded_transactions":    "{n} Transaktionen für den Datumsbereich geladen ({env}).",
        "load_failed":            "Laden fehlgeschlagen ({env}): {exc}",
        "refreshed":              "Aktualisiert — {n} Transaktionen ({env}).",
        "refresh_failed":         "Aktualisierung fehlgeschlagen ({env}): {exc}",
        "no_pp_creds":            "Keine PayPal-Anmeldedaten gespeichert — konfigurieren Sie diese in ⚙️ Einstellungen.",
        "connecting_paypal":      "Verbinde mit PayPal…",
        "could_not_get_token":    "PayPal-Token konnte nicht abgerufen werden: {result}",
        "tickets_per_category":   "Ticketkategorien pro Abend",
        "building_pdf":           "PDF wird erstellt…",

        # ── Reconciliation — DataFrame column display names ──────────────────
        "col_performance_date":   "Aufführungsdatum",
        "col_transactions":       "Transaktionen",
        "col_gross":              "Brutto (€)",
        "col_fees":               "Gebühren (€)",
        "col_net":                "Netto (€)",
        "col_total_tickets":      "Gesamtanzahl Tickets",
        "col_total_label":        "Transaktionen Gesamt",
        "col_stats_total":        "Gesamt",

        # ── PDF — section headers ────────────────────────────────────────────
        "pdf_header":             "SSG Online Ticketverkauf",
        "pdf_page":               "Seite {n}",
        "pdf_production":         "Produktion: {show}",
        "pdf_period":             "Zeitraum: {start}  →  {end}",
        "pdf_generated":          "Erstellt am: {date}",
        "pdf_enter_values":       "Bitte geben Sie die folgenden Werte in Ihre Abrechnung ein",
        "pdf_totals_section":     "Gesamtanzahl",
        "pdf_stats_section":      "Statistik",
        "pdf_categories_section": "Ticketkategorien",
        "pdf_yield_section":      "Ertrag & Kapazität",
        "pdf_revenue_trend":      "Umsatzentwicklung",
        "pdf_no_perf_data":       "Keine Aufführungsdaten verfügbar.",
        "pdf_no_cat_data":        "Keine Kategorie- oder Aufführungsdaten verfügbar.",
        "pdf_no_sales_data":      "Keine Verkaufsdaten verfügbar für den Trendgraph.",
        "pdf_total_tickets_sold": "Gesamtanzahl Tickets verkauft",
        "pdf_total_revenue":      "Gesamtumsatz",
        "pdf_capacity":           "Kapazität",
        "pdf_sell_through":       "Auslastungsgrad",
        "pdf_rev_per_seat":       "Umsatz / Sitzplatz",
        "pdf_seats_suffix":       "Sitzplätze",
        "pdf_sold_label":         "ausgelastet",
        "pdf_pie_title":          "Details zu den Ticketkategorien",
        "pdf_trend_title":        "Kumulative Ticketverkäufe",
        "pdf_trend_x":            "Tage seit erstem Verkauf",
        "pdf_trend_y":            "Gesamtzahl der verkauften Tickets",
        "pdf_daily_title":        "Tägliche Ticketverkäufe",
        "pdf_daily_x":            "Datum",
        "pdf_daily_y":            "Verkaufte Tickets",
        "pdf_chart_title":        "Ticketkategorien pro Abend",
        "pdf_chart_x":            "Aufführungsdatum",
        "pdf_chart_legend":       "Kategorie",
        "pdf_first_sale":         "Erster Verkauf",
        "pdf_last_sale":          "Letzter Verkauf",
        "pdf_selling_window":     "Verkaufszeitraum",
        "pdf_peak_day":           "Höchster Tag",
        "pdf_peak_tickets":       "Höchste Ticketanzahl",
        "pdf_days_suffix":        "Tage",
        "pdf_day_prefix":         "Tag",
        "pdf_recon_section":      "Ticket Tailor / PayPal Abgleich",
        "pdf_tt_gross":           "Ticket Tailor Brutto",
        "pdf_pp_gross":           "PayPal Brutto",
        "pdf_diff":               "Differenz",
        "pdf_recon_passed":       "Abgleich erfolgreich — Werte stimmen überein.",
        "pdf_recon_diff":         "Unterschied von {diff:.2f} €. Prüfen Sie auf Rückerstattungen oder Transaktionen außerhalb des Zeitraums.",
    },
}


def t(key: str, **kwargs) -> str:
    """Return the translated string for *key* in the current session language.

    Falls back to English if the key is missing in the selected language,
    then to the key itself if missing in English too.
    Extra keyword arguments are interpolated via str.format().
    """
    lang   = st.session_state.get("lang", "en")
    text   = (_STRINGS.get(lang, {}).get(key)
              or _STRINGS["en"].get(key)
              or key)
    return text.format(**kwargs) if kwargs else text


def col_map() -> dict[str, str]:
    """Rename dict for reconciliation DataFrames: English internal name → display name."""
    return {
        "Performance Date": t("col_performance_date"),
        "Transactions":     t("col_transactions"),
        "Gross (€)":        t("col_gross"),
        "Fees (€)":         t("col_fees"),
        "Net (€)":          t("col_net"),
        "Total Tickets":    t("col_total_tickets"),
    }
