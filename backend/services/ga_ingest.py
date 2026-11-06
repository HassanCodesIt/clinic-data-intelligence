import json
import time
from typing import Any, Callable

import httpx

from ..config import REQUEST_TIMEOUT
from ..db import connect, init_db, utc_now

LAYER_URL = "https://services.ga.gov.au/gis/rest/services/National_HealthDirect_Health_Facilities/MapServer/0"
SOURCE_NAME = "GENERAL_PRACTICE"
STATES = {"ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"}


def _normalise_state(value: Any) -> str:
    state = str(value or "").strip().upper()
    return state if state in STATES else "Unknown"


def _request(params: dict[str, Any]) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
                response = client.get(f"{LAYER_URL}/query", params=params)
                response.raise_for_status()
                payload = response.json()
                if "error" in payload:
                    raise RuntimeError(payload["error"].get("message", "ArcGIS query failed"))
                return payload
        except (httpx.HTTPError, ValueError, RuntimeError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2**attempt)
    raise RuntimeError(f"Source ingestion failed: {last_error}") from last_error


def ingest(state: str | None = None, progress: Callable[[int], None] | None = None) -> dict[str, int]:
    init_db()
    requested = state.strip().upper() if state else "ALL"
    where = "1=1" if requested == "ALL" else f"STATE = '{requested.replace(chr(39), chr(39) * 2)}'"
    offset = 0
    total = 0
    with connect() as db:
        while True:
            payload = _request({
                "where": where,
                "outFields": "*",
                "returnGeometry": "true",
                "resultOffset": offset,
                "resultRecordCount": 1000,
                "f": "json",
            })
            features = payload.get("features", [])
            for feature in features:
                attrs = feature.get("attributes", {})
                geometry = feature.get("geometry") or {}
                source_id = str(attrs.get("OBJECTID") or attrs.get("objectid") or "")
                if not source_id:
                    continue
                state_value = _normalise_state(attrs.get("STATE") or attrs.get("state"))
                postcode = str(attrs.get("POSTCODE") or attrs.get("postcode") or "")
                name = str(attrs.get("ORGANISATION_NAME") or attrs.get("organisation_name") or "")
                address = str(attrs.get("ADDRESS") or attrs.get("address") or "")
                suburb = str(attrs.get("SUBURB") or attrs.get("suburb") or "")
                latitude = geometry.get("y", attrs.get("LATITUDE") or attrs.get("latitude"))
                longitude = geometry.get("x", attrs.get("LONGITUDE") or attrs.get("longitude"))
                db.execute(
                    """
                    INSERT INTO practices(source_id,name,address,suburb,state,postcode,latitude,longitude,raw_json)
                    VALUES(?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(source_id) DO UPDATE SET
                    name=excluded.name,address=excluded.address,suburb=excluded.suburb,
                    state=excluded.state,postcode=excluded.postcode,latitude=excluded.latitude,
                    longitude=excluded.longitude,raw_json=excluded.raw_json
                    """,
                    (source_id, name, address, suburb, state_value, postcode, latitude, longitude, json.dumps(attrs)),
                )
                total += 1
            if progress:
                progress(total)
            if not payload.get("exceededTransferLimit") or not features:
                break
            offset += len(features)
        db.execute(
            "INSERT OR REPLACE INTO ingestion_metadata(id,source_name,source_link,ingested_at) VALUES(1,?,?,?)",
            (SOURCE_NAME, LAYER_URL, utc_now()),
        )
    return state_counts()


def state_counts() -> dict[str, int]:
    with connect() as db:
        return {row["state"]: row["count"] for row in db.execute("SELECT state, COUNT(*) count FROM practices WHERE name <> '' AND state <> 'Unknown' GROUP BY state ORDER BY state")}
