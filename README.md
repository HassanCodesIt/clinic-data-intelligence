# GP Atlas AU

GP Atlas AU is a SQLite-backed browser for Australian general-practice records sourced from Geoscience Australia. The snapshot includes source fields, normalised state/postcode/coordinates, source provenance, and saved AI enrichment results.

## Run locally on Windows

### 1. Clone the repository

```powershell
git clone https://github.com/HassanCodesIt/clinic-data-intelligence.git
cd clinic-data-intelligence
```

### 2. Create and activate a virtual environment

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run this once, then activate again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure environment variables

```powershell
Copy-Item .env.example .env
notepad .env
```

Replace `your_key_here` with your Groq API key. The key is required for
**Search in your own words**, website finding, website enrichment, and outreach
drafts. Browsing and basic database features work without it.

### 5. Load the practice data

Load all Australian states and territories:

```powershell
python -c "from backend.services.ga_ingest import ingest; print(ingest())"
```

To load only one state, for example Victoria:

```powershell
python -c "from backend.services.ga_ingest import ingest; print(ingest('VIC'))"
```

### 6. Start the application

```powershell
python -m uvicorn backend.main:app --reload
```

Keep this PowerShell window open while using the app.

### 7. Open the application

Open `http://127.0.0.1:8000` in your browser.

The application needs internet access to download ArcGIS data, load the
Leaflet map, search DuckDuckGo, and fetch clinic websites. If the database is
empty, click **Load data** in the application instead of running ingestion
manually.

### 8. Run the tests (optional)

In another PowerShell window:

```powershell
cd clinic-data-intelligence
.venv\Scripts\Activate.ps1
python -m pytest -q
```

## Architecture

- SQLite stores practices, ingestion metadata, website candidates, enrichments, outreach drafts, and external-service cache entries.
- FastAPI serves database-backed filters, search, sorting, pagination, map results, statistics, details, and CSV export.
- Website search uses DuckDuckGo only after a user action. Groq uses `openai/gpt-oss-120b` through its OpenAI-compatible endpoint.
- External-service cache entries have expiry times and are removed when the application starts.
- Website fetching requires HTTPS, checks every redirect, blocks private addresses, applies `robots.txt`, and enforces a streaming size limit.

## Safety and limitations

The public source is a point-in-time snapshot and may omit contact details. AI results must be reviewed. Outreach is an editable draft only and is never sent. The app handles practice-level business information, not patient information, and does not provide medical advice. Search and website enrichment are user-triggered; there is no bulk crawling.

Create a CSV sample from the current snapshot with Export CSV. Keep the Groq key in `.env`; do not place secrets in source control.
