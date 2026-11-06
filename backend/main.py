import csv
import io
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .db import connect, init_db, utc_now
from .models import AskRequest, AskResponse, EnrichRequest, Enrichment, OutreachDraft, Practice, PracticeFilter, PracticePage, WebsiteCandidate
from .services.fetcher import fetch_page
from .services.ga_ingest import LAYER_URL, SOURCE_NAME, ingest, state_counts
from .services.llm import ask_json
from .services.prompts import ASK_SYSTEM, ENRICH_SYSTEM, OUTREACH_SYSTEM, PROMPT_VERSION, WEBSITE_SYSTEM
from .services.search import search_web

app = FastAPI(title="GP Atlas AU", version="2.0.0")
ROOT = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")


@app.on_event("startup")
def startup() -> None:
    init_db()


def _where(filters: PracticeFilter) -> tuple[str, list[str]]:
    clauses = ["name <> ''", "state <> 'Unknown'"]
    params: list[str] = []
    if filters.state:
        clauses.append("state = ?")
        params.append(filters.state)
    if filters.postcode:
        clauses.append("postcode = ?")
        params.append(filters.postcode)
    if filters.q:
        clauses.append("(name LIKE ? OR suburb LIKE ? OR address LIKE ?)")
        value = f"%{filters.q}%"
        params.extend([value, value, value])
    return " AND ".join(clauses), params


def _practice(row: Any) -> Practice:
    raw = json.loads(row["raw_json"])
    return Practice(
        id=row["id"], name=row["name"] or "not available", address=row["address"],
        suburb=row["suburb"], state=row["state"], postcode=row["postcode"],
        lat=row["latitude"], lon=row["longitude"], fields=raw,
    )


def _page(filters: PracticeFilter, page: int, page_size: int, sort_by: str, sort_dir: str) -> PracticePage:
    allowed = {"name", "address", "suburb", "state", "postcode"}
    sort_column = sort_by if sort_by in allowed else "name"
    direction = "DESC" if sort_dir.lower() == "desc" else "ASC"
    where, params = _where(filters)
    bounded = min(page_size, 100)
    with connect() as db:
        total = db.execute(f"SELECT COUNT(*) FROM practices WHERE {where}", params).fetchone()[0]
        without = db.execute(f"SELECT COUNT(*) FROM practices WHERE {where} AND (latitude IS NULL OR longitude IS NULL)", params).fetchone()[0]
        rows = db.execute(
            f"SELECT * FROM practices WHERE {where} ORDER BY {sort_column} {direction}, id LIMIT ? OFFSET ?",
            [*params, bounded, (page - 1) * bounded],
        ).fetchall()
    return PracticePage(items=[_practice(row) for row in rows], page=page, page_size=bounded, total=total, without_coordinates=without)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "frontend" / "index.html")


@app.get("/api/practices", response_model=PracticePage)
def practices(
    state: str | None = None, postcode: str | None = None, q: str | None = None,
    sort_by: str = Query("name"), sort_dir: str = Query("asc"),
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
) -> PracticePage:
    return _page(PracticeFilter(state=state, postcode=postcode, q=q), page, page_size, sort_by, sort_dir)


@app.get("/api/practices/export.csv")
def export_csv(state: str | None = None, postcode: str | None = None, q: str | None = None) -> StreamingResponse:
    filters = PracticeFilter(state=state, postcode=postcode, q=q)
    where, params = _where(filters)
    with connect() as db:
        rows = db.execute(f"SELECT * FROM practices WHERE {where} ORDER BY name, id", params).fetchall()
    output = io.StringIO()
    fieldnames = ["id", "name", "address", "suburb", "state", "postcode", "lat", "lon"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows({"id": row["id"], "name": row["name"], "address": row["address"], "suburb": row["suburb"], "state": row["state"], "postcode": row["postcode"], "lat": row["latitude"], "lon": row["longitude"]} for row in rows)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=practices.csv"})


@app.get("/api/stats")
def stats() -> dict[str, Any]:
    with connect() as db:
        total = db.execute("SELECT COUNT(*) FROM practices WHERE name <> '' AND state <> 'Unknown'").fetchone()[0]
        states = [{"state": row["state"], "count": row["count"]} for row in db.execute("SELECT state, COUNT(*) count FROM practices WHERE name <> '' AND state <> 'Unknown' GROUP BY state ORDER BY state")]
    return {"total": total, "states": states}


@app.get("/api/metadata")
def metadata() -> dict[str, str | None]:
    with connect() as db:
        row = db.execute("SELECT source_name, source_link, ingested_at FROM ingestion_metadata WHERE id=1").fetchone()
    return {"source_name": row["source_name"] if row else SOURCE_NAME, "source_url": row["source_link"] if row else LAYER_URL, "ingested_at": row["ingested_at"] if row else None}


@app.post("/api/ingest")
def run_ingest(state: str | None = None) -> dict[str, Any]:
    try:
        return {"states": ingest(state), "message": "Data loaded successfully."}
    except RuntimeError as exc:
        raise HTTPException(503, "Data could not be loaded. Please retry.") from exc


@app.post("/api/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    try:
        parsed = ask_json(ASK_SYSTEM, request.question, PROMPT_VERSION, PracticeFilter)
        return AskResponse(filter=parsed, results=_page(parsed, 1, 25, "name", "asc"))
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(503, "The AI could not validate that filter. Please rephrase and retry.") from exc


def _record_or_404(practice_id: int) -> Practice:
    with connect() as db:
        row = db.execute("SELECT * FROM practices WHERE id=?", (practice_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Practice not found.")
    return _practice(row)


@app.post("/api/practices/{practice_id}/find-website", response_model=list[WebsiteCandidate])
def find_website(practice_id: int) -> list[WebsiteCandidate]:
    practice = _record_or_404(practice_id)
    try:
        results = search_web(f"{practice.name} {practice.suburb} {practice.state} GP clinic")
        if not results:
            return []
        class Pick(PracticeFilter):
            url: str | None = None
            confidence: float = 0
            reason: str = ""
        pick = ask_json(WEBSITE_SYSTEM, json.dumps({"practice": practice.model_dump(), "results": results}), PROMPT_VERSION, Pick)
        selected = next((item for item in results if item["url"] == pick.url), None)
        candidates = [WebsiteCandidate(id=results.index(selected), url=selected["url"], title=selected["title"], snippet=selected["snippet"], confidence=pick.confidence, reason=pick.reason)] if selected else []
        with connect() as db:
            for candidate in candidates:
                db.execute("INSERT INTO website_candidates(practice_id,result_json,created_at) VALUES(?,?,?)", (practice_id, candidate.model_dump_json(), utc_now()))
        return candidates
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post("/api/practices/{practice_id}/website-candidates/{candidate_id}/confirm")
def confirm_website(practice_id: int, candidate_id: int) -> dict[str, str]:
    _record_or_404(practice_id)
    return {"status": "confirmed"}


@app.post("/api/practices/{practice_id}/enrich", response_model=Enrichment)
def enrich(practice_id: int, request: EnrichRequest) -> Enrichment:
    _record_or_404(practice_id)
    try:
        text = fetch_page(str(request.website))
        result = ask_json(ENRICH_SYSTEM, text, PROMPT_VERSION, Enrichment)
        valid = {field: snippet for field, snippet in result.source_snippets.items() if snippet and snippet in text}
        for field in ("email", "phone", "bulk_billing", "hours"):
            if getattr(result, field) and field not in valid:
                setattr(result, field, "")
        for field in ("services", "languages"):
            if getattr(result, field) and field not in valid:
                setattr(result, field, [])
        result.source_snippets = valid
        result.confidence = {field: value for field, value in result.confidence.items() if field in valid}
        with connect() as db:
            db.execute("INSERT OR REPLACE INTO enrichments(practice_id,result_json,updated_at) VALUES(?,?,?)", (practice_id, result.model_dump_json(), utc_now()))
        return result
    except (RuntimeError, ValueError, PermissionError, OSError) as exc:
        raise HTTPException(503, "That website could not be safely fetched. Please try another URL.") from exc


@app.post("/api/practices/{practice_id}/outreach", response_model=OutreachDraft)
def outreach(practice_id: int) -> OutreachDraft:
    practice = _record_or_404(practice_id)
    try:
        result = ask_json(OUTREACH_SYSTEM, json.dumps({"practice": practice.model_dump()}), PROMPT_VERSION, OutreachDraft)
        with connect() as db:
            db.execute("INSERT OR REPLACE INTO outreach_drafts(practice_id,result_json,updated_at) VALUES(?,?,?)", (practice_id, result.model_dump_json(), utc_now()))
        return result
    except RuntimeError as exc:
        raise HTTPException(503, "The outreach draft could not be generated. Please retry.") from exc


@app.get("/api/practices/{practice_id}/details")
def practice_details(practice_id: int) -> dict[str, Any]:
    practice = _record_or_404(practice_id)
    with connect() as db:
        enrichment = db.execute("SELECT result_json FROM enrichments WHERE practice_id=?", (practice_id,)).fetchone()
        candidates = db.execute("SELECT result_json FROM website_candidates WHERE practice_id=? ORDER BY id", (practice_id,)).fetchall()
        outreach_row = db.execute("SELECT result_json FROM outreach_drafts WHERE practice_id=?", (practice_id,)).fetchone()
    return {
        "source_data": practice.fields, "source_provenance": "Source data",
        "enrichment": json.loads(enrichment["result_json"]) if enrichment else None, "enrichment_provenance": "Web page",
        "candidates": [json.loads(row["result_json"]) for row in candidates], "website_provenance": "AI-generated",
        "outreach": json.loads(outreach_row["result_json"]) if outreach_row else None, "outreach_provenance": "AI-generated",
    }
