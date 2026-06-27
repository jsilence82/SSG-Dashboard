# SSG Ticket Sales Dashboard

A local Streamlit dashboard for analysing theatre ticket sales from [Ticket Tailor](https://www.tickettailor.com), with optional PayPal reconciliation.

---

## Features

### Analytics tab
| Sub-tab | What it shows |
|---|---|
| Overview | Revenue and ticket totals per show (bar charts) |
| Per-show breakdown | Category split per show (pie charts) |
| Show ranking | Shows ranked by tickets sold and revenue |
| Categories | Ticket category breakdown across all shows |
| Sales trend | Tickets sold over time (daily / weekly) |
| Yield & Capacity | Sold vs. capacity per show with a fill-rate metric |
| Audience Retention | Repeat buyer analysis by email |
| Multi-night | Per-night breakdown for shows with multiple performances |
| Detail table | Full filterable row-level data |

### Reconciliation Report tab
Cross-references Ticket Tailor order data against PayPal transaction history. Generates a Totals sheet (gross / fees / net per performance night) and a Statistics sheet (ticket categories per night). Detects transferred tickets (voided in TT but PayPal charge still valid) and flags unmatched PayPal transactions.

### Settings tab
- Enter and test your Ticket Tailor API key
- Enter PayPal Client ID and Client Secret (stored in the OS keychain — never written to disk)
- Configure column mappings if your data uses custom column names

---

## Project structure

```
SSG Ticket Dashboard/
├── app.py                        # Streamlit entry point
├── requirements.txt
└── ssg_dashboard/
    ├── main.py                   # Startup logic and page orchestration
    ├── sidebar.py                # Cache status and load/refresh controls
    ├── config.py                 # Shared paths and constants
    ├── mapping.py                # Column-mapping UI and canonical builder
    ├── api/
    │   ├── tickettailor.py       # Ticket Tailor REST client + raw data processing
    │   └── paypal.py             # PayPal OAuth2 token + Transaction Search client
    ├── persistence/
    │   ├── canonical.py          # Read/write the processed canonical cache
    │   ├── settings.py           # Non-secret settings JSON + keychain credential helpers
    │   ├── tt_cache.py           # Raw Ticket Tailor API snapshot cache
    │   └── paypal_cache.py       # Smart date-range-aware PayPal transaction cache
    └── sections/
        ├── dashboard.py          # Top-level tab assembly
        ├── kpis.py               # Summary metric cards
        ├── overview.py           # Bar and pie charts
        ├── ranking.py            # Show ranking table
        ├── categories.py         # Category breakdown
        ├── trend.py              # Sales-over-time chart
        ├── yield_capacity.py     # Capacity fill-rate analysis
        ├── repeat_buyers.py      # Repeat buyer / audience retention
        ├── multi_night.py        # Multi-night per-performance breakdown
        ├── detail.py             # Filterable detail table
        ├── reconciliation.py     # PayPal reconciliation report
        └── settings.py           # Settings tab UI
```

### Runtime data (gitignored)

All files in `data/` are created automatically on first run and are excluded from version control.

| File | Contents |
|---|---|
| `data/ssg_settings.json` | Column mapping, capacity overrides, sandbox flag — no secrets |
| `data/ssg_cache.json` | Processed canonical ticket data (rebuilt from TT cache on startup) |
| `data/tt_raw_cache.json` | Raw Ticket Tailor API snapshot (tickets, events, orders) |
| `data/paypal_cache.json` | PayPal transactions with covered date-range metadata |

API credentials (Ticket Tailor key, PayPal Client ID and Secret) are stored in the **OS keychain** via the `keyring` library and are never written to disk.

---

## Prerequisites

- **Python 3.10+**
- A [Ticket Tailor](https://www.tickettailor.com) account with API access enabled
- *(Optional)* A PayPal REST API app with the **Transaction Search** feature enabled
  - Go to [developer.paypal.com](https://developer.paypal.com) → My Apps & Credentials → select your app → Live features → tick **Transaction Search** → Save

---

## Installation

```bash
# 1. Clone the repository
git clone <repo-url>
cd "SSG Ticket Dashboard"

# 2. (Recommended) Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the dashboard
streamlit run app.py
```

The `data/` directory is created automatically on first run.

---

## First-time configuration

1. Open the **⚙️ Settings** tab
2. Enter your Ticket Tailor API key and click **Save key**
3. Click **Refresh from API** to fetch your ticket data
4. *(Optional)* Enter your PayPal Client ID and Client Secret and click **Save PayPal credentials**, then **Test & get token** to connect
5. Set up column mappings if prompted (required fields: Show and Category)

On subsequent runs the dashboard loads from the local cache automatically — no API call needed unless you click Refresh.
