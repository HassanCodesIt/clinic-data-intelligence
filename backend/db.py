import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from .config import DB_PATH


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    return connection


def init_db() -> None:
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS practices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL DEFAULT '',
                address TEXT NOT NULL DEFAULT '',
                suburb TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL DEFAULT 'Unknown',
                postcode TEXT NOT NULL DEFAULT '',
                latitude REAL,
                longitude REAL,
                raw_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_practices_state ON practices(state);
            CREATE INDEX IF NOT EXISTS idx_practices_postcode ON practices(postcode);
            CREATE TABLE IF NOT EXISTS ingestion_metadata (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                source_name TEXT NOT NULL,
                source_link TEXT NOT NULL,
                ingested_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS enrichments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                practice_id INTEGER NOT NULL UNIQUE,
                result_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(practice_id) REFERENCES practices(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS website_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                practice_id INTEGER NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(practice_id) REFERENCES practices(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS outreach_drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                practice_id INTEGER NOT NULL UNIQUE,
                result_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(practice_id) REFERENCES practices(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS cache (
                cache_key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                expires_at REAL NOT NULL,
                created_at REAL NOT NULL
            );
            """
        )
        db.execute("DELETE FROM cache WHERE expires_at <= strftime('%s','now')")


def cache_get(key: str) -> Any | None:
    with connect() as db:
        row = db.execute("SELECT value_json FROM cache WHERE cache_key=? AND expires_at>?", (key, datetime.now().timestamp())).fetchone()
        return json.loads(row["value_json"]) if row else None


def cache_set(key: str, value: Any, ttl: int) -> None:
    now = datetime.now().timestamp()
    with connect() as db:
        db.execute(
            "INSERT OR REPLACE INTO cache(cache_key,value_json,expires_at,created_at) VALUES(?,?,?,?)",
            (key, json.dumps(value), now + ttl, now),
        )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
