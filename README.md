# SSG Ticket Sales Dashboard

A Streamlit dashboard for analysing theatre ticket sales from [Ticket Tailor](https://www.tickettailor.com), with optional PayPal reconciliation.

> **Deployed for internal testing and development on Streamlit Community Cloud.**
> Access requires a username and password — contact Jeff to request access.

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
- Test your Ticket Tailor API connection and refresh data
- Configure PayPal connection and run reconciliation
- Configure column mappings if your data uses custom column names

---

## Accessing the deployed app

The app is hosted on **Streamlit Community Cloud** for internal use.

- Log in with your username and password
- After loading, click **Refresh from API** in the sidebar if no data is shown (the cloud instance does not retain cached data between restarts)
- The app may take 30–60 seconds to wake up after a period of inactivity — this is normal on the free tier

> **Credentials are managed centrally.** API keys and PayPal secrets are configured server-side and are not editable through the app UI when running on the cloud.

---

## Running locally

If you need to run the app on your own machine (e.g. for development or offline use):

### Prerequisites

- **Python 3.10 or later** — download from [python.org](https://www.python.org/downloads/) if needed
- A [Ticket Tailor](https://www.tickettailor.com) account with API access enabled
- *(Optional)* A PayPal REST API app with the **Transaction Search** feature enabled

### macOS setup

```bash
# 1. Create a virtual environment
python3 -m venv .venv

# 2. Install dependencies
.venv/bin/pip install -r requirements.txt

# 3. Sign the .app bundle so macOS will allow it to launch
./sign_app.sh

# 4. Copy the secrets template and fill in your credentials
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with your actual API keys
```

### Windows setup

```bat
REM 1. Create a virtual environment
python -m venv .venv

REM 2. Install dependencies
.venv\Scripts\pip install -r requirements.txt

REM 3. Copy the secrets template and fill in your credentials
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
REM Edit .streamlit\secrets.toml with your actual API keys
```

### Opening the app locally

| Method | How |
|---|---|
| macOS double-click | Double-click **SSG Ticket Dashboard.app** in Finder |
| macOS terminal | `./run.sh` |
| Windows double-click | Double-click **run.bat** in File Explorer |
| Windows terminal | `run.bat` |

Press `Ctrl+C` in the terminal window to stop the server.

**First time on macOS:** the system may show a security warning on first launch. Go to **System Settings → Privacy & Security** and click **Open Anyway**.

### Local configuration

When running locally, credentials are entered via the **⚙️ Settings** tab and stored securely in the OS credential store (macOS Keychain / Windows Credential Manager). They are never written to disk as plain text.

---

## Deployment (for administrators)

### Adding or changing user passwords

1. Run the password hash generator:
   ```bash
   .venv/bin/python3 generate_auth.py
   ```
2. Copy the printed hash into `auth.yaml` under the relevant username
3. Commit and push — the cloud app redeploys automatically

### Updating API credentials on the cloud

Go to the Streamlit Cloud dashboard → **App settings → Secrets** and update the relevant value. The app restarts automatically after saving.

### Known cloud limitations

- **Data does not persist across restarts.** The `data/` cache is wiped on each restart or sleep/wake cycle. Users need to click **Refresh from API** after a cold start.
- **The app sleeps after ~7 days of inactivity** on the free tier. The first load after sleep takes 30–60 seconds.

---

## Project structure

```
SSG Ticket Dashboard/
├── app.py                        # Streamlit entry point (includes auth gate)
├── auth.yaml                     # User credentials (bcrypt hashes — safe to commit)
├── run.sh                        # macOS/Linux terminal launcher
├── run.bat                       # Windows launcher
├── sign_app.sh                   # Re-signs the .app bundle after edits (macOS only)
├── requirements.txt
├── SSG Ticket Dashboard.app/     # macOS double-click launcher
├── .streamlit/
│   └── secrets.toml              # Local dev secrets (gitignored — never commit)
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
    │   ├── settings.py           # Credential abstraction (secrets → env → keyring)
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
        ├── pdf_export.py         # PDF export for reconciliation reports
        └── settings.py           # Settings tab UI
```

### Credential storage

| Context | Where credentials live |
|---|---|
| Streamlit Community Cloud | Streamlit secrets panel (encrypted, server-side) |
| Local — macOS | macOS Keychain via `keyring` |
| Local — Windows | Windows Credential Manager via `keyring` + `pywin32-ctypes` |
| Local — alternative | `.streamlit/secrets.toml` (gitignored) |

### Runtime data (gitignored)

| File | Contents |
|---|---|
| `data/ssg_settings.json` | Column mapping, capacity overrides, sandbox flag |
| `data/ssg_cache.json` | Processed canonical ticket data |
| `data/tt_raw_cache.json` | Raw Ticket Tailor API snapshot |
| `data/paypal_cache.json` | PayPal transactions with date-range metadata |
