import json
import pytest

from backend import db
from backend.main import _page
from backend.models import Enrichment, PracticeFilter
from backend.services import fetcher
from backend.services import ga_ingest


def setup_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()


def test_ingestion_is_idempotent_and_supports_two_states(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path)
    pages = [{
        "features": [
            {"attributes": {"OBJECTID": 1, "ORGANISATION_NAME": "A", "STATE": "VIC", "POSTCODE": 3000}},
            {"attributes": {"OBJECTID": 2, "ORGANISATION_NAME": "B", "STATE": "NSW", "POSTCODE": 2000}},
        ]
    }]
    monkeypatch.setattr(ga_ingest, "_request", lambda params: pages.pop(0))
    ga_ingest.ingest()
    monkeypatch.setattr(ga_ingest, "_request", lambda params: {"features": []})
    ga_ingest.ingest()
    assert ga_ingest.state_counts() == {"NSW": 1, "VIC": 1}
    assert _page(PracticeFilter(state="VIC"), 1, 25, "name", "asc").items[0].state == "VIC"


def test_sqlite_cache_hit_and_expiry(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path)
    db.cache_set("key", {"value": 1}, 60)
    assert db.cache_get("key") == {"value": 1}
    with db.connect() as connection:
        connection.execute("UPDATE cache SET expires_at=0 WHERE cache_key='key'")
    assert db.cache_get("key") is None


def test_empty_database_is_reported_by_stats(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path)
    from backend.main import stats
    assert stats() == {"total": 0, "states": []}


def test_snippet_verification_keeps_only_page_values():
    text = "Email contact@example.test is available."
    result = Enrichment(
        email="contact@example.test",
        phone="0400000000",
        source_snippets={"email": "contact@example.test", "phone": "missing"},
    )
    assert {key: value for key, value in result.source_snippets.items() if value in text} == {"email": "contact@example.test"}


def test_fetcher_blocks_unsafe_urls():
    for url in ("http://example.test", "https://127.0.0.1", "https://10.0.0.1", "https://169.254.1.1"):
        with pytest.raises(ValueError):
            fetcher._public_host(url)
