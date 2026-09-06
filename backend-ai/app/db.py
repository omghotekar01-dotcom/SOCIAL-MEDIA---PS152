from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Iterable

from .config import get_settings
from .schemas import SocialEvent


class EventStore:
    """Small, zero-config SQLite store for the hackathon runtime.

    The table intentionally stores a compact searchable envelope plus the full
    normalized event JSON. That keeps the MVP simple while preserving a clean
    migration path to PostgreSQL later.
    """

    def __init__(self, path: Path | None = None) -> None:
        settings = get_settings()
        self.path = path or settings.sqlite_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS social_events (
                    id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    source_event_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    ingested_at TEXT NOT NULL,
                    author_pseudo_id TEXT,
                    narrative_cluster_id TEXT,
                    source_mode TEXT NOT NULL,
                    raw_hash TEXT,
                    payload TEXT NOT NULL,
                    UNIQUE(platform, source_event_id)
                );
                CREATE INDEX IF NOT EXISTS idx_social_events_created
                    ON social_events(created_at);
                CREATE INDEX IF NOT EXISTS idx_social_events_platform
                    ON social_events(platform);
                CREATE INDEX IF NOT EXISTS idx_social_events_narrative
                    ON social_events(narrative_cluster_id);

                CREATE TABLE IF NOT EXISTS connector_runs (
                    run_id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    state TEXT NOT NULL,
                    detail TEXT,
                    event_count INTEGER DEFAULT 0
                );
                """
            )

    def upsert(self, event: SocialEvent) -> None:
        self.upsert_many([event])

    def upsert_many(self, events: Iterable[SocialEvent]) -> int:
        rows = []
        for event in events:
            rows.append(
                (
                    event.id,
                    event.platform,
                    event.source_event_id,
                    event.created_at.isoformat(),
                    event.ingested_at.isoformat(),
                    event.author_pseudo_id,
                    event.narrative_cluster_id,
                    event.source_mode,
                    event.raw_hash,
                    event.model_dump_json(),
                )
            )
        if not rows:
            return 0
        with self._lock, self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO social_events(
                    id, platform, source_event_id, created_at, ingested_at,
                    author_pseudo_id, narrative_cluster_id, source_mode,
                    raw_hash, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(platform, source_event_id) DO UPDATE SET
                    created_at=excluded.created_at,
                    ingested_at=excluded.ingested_at,
                    author_pseudo_id=excluded.author_pseudo_id,
                    narrative_cluster_id=excluded.narrative_cluster_id,
                    source_mode=excluded.source_mode,
                    raw_hash=excluded.raw_hash,
                    payload=excluded.payload
                """,
                rows,
            )
        return len(rows)

    def list_events(self, limit: int = 5000, platform: str | None = None) -> list[SocialEvent]:
        limit = max(1, min(limit, 20000))
        with self._connect() as conn:
            if platform:
                rows = conn.execute(
                    "SELECT payload FROM social_events WHERE platform=? ORDER BY created_at ASC LIMIT ?",
                    (platform, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload FROM social_events ORDER BY created_at ASC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [SocialEvent.model_validate_json(row["payload"]) for row in rows]

    def count(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM social_events").fetchone()[0])

    def clear(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM social_events")
            conn.execute("DELETE FROM connector_runs")

    def delete_event(self, event_id: str) -> bool:
        with self._lock, self._connect() as conn:
            cursor = conn.execute("DELETE FROM social_events WHERE id=?", (event_id,))
            return cursor.rowcount > 0


store = EventStore()
