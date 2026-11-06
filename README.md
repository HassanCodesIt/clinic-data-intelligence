# GP Atlas AU

GP Atlas AU is a SQLite-backed browser for Australian general-practice records sourced from Geoscience Australia. The snapshot includes source fields, normalised state/postcode/coordinates, source provenance, and saved AI enrichment results.

## Run locally

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Add GROQ_API_KEY to .env for AI actions
python -c "from backend.services.ga_ingest import ingest; print(ingest())"
uvicorn backend.main:app --reload
```

The ingestion command loads every state and territory. Use `python -c "from backend.services.ga_ingest import ingest; print(ingest('VIC'))"` for one state. If the database is empty, the app shows a Load data button.

## Architecture

- SQLite stores practices, ingestion metadata, website candidates, enrichments, outreach drafts, and external-service cache entries.
- FastAPI serves database-backed filters, search, sorting, pagination, map results, statistics, details, and CSV export.
- Website search uses DuckDuckGo only after a user action. Groq uses `openai/gpt-oss-120b` through its OpenAI-compatible endpoint.
- External-service cache entries have expiry times and are removed when the application starts.
- Website fetching requires HTTPS, checks every redirect, blocks private addresses, applies `robots.txt`, and enforces a streaming size limit.

## Safety and limitations

The public source is a point-in-time snapshot and may omit contact details. AI results must be reviewed. Outreach is an editable draft only and is never sent. The app handles practice-level business information, not patient information, and does not provide medical advice. Search and website enrichment are user-triggered; there is no bulk crawling.

Create a CSV sample from the current snapshot with Export CSV. Keep the Groq key in `.env`; do not place secrets in source control.
