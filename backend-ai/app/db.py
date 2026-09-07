from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .config import get_settings
from .schemas import SocialEvent, SocialEventIn


JSON_FIELDS = {
    "mentions",
    "hashtags",
    "urls",
    "engagement",
    "public_profile",
    "emotion_scores",
    "topic_terms",
}


class EventStore:
    def __init__(self, db_path: Path | None = None):
        self.settings = get_settings()
        self.db_path = db_path or self.settings.sqlite_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    source_event_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    author_platform_id TEXT,
                    author_pseudo_id TEXT,
                    author_display TEXT,
                    text TEXT NOT NULL,
                    language TEXT,
                    created_at TEXT NOT NULL,
                    ingested_at TEXT NOT NULL,
                    url TEXT,
                    parent_event_id TEXT,
                    conversation_id TEXT,
                    mentions TEXT NOT NULL DEFAULT '[]',
                    hashtags TEXT NOT NULL DEFAULT '[]',
                    urls TEXT NOT NULL DEFAULT '[]',
                    engagement TEXT NOT NULL DEFAULT '{}',
                    public_profile TEXT NOT NULL DEFAULT '{}',
                    source_mode TEXT NOT NULL,
                    connector_run_id TEXT,
                    raw_hash TEXT NOT NULL,
                    sentiment_label TEXT,
                    sentiment_score REAL,
                    emotion_scores TEXT NOT NULL DEFAULT '{}',
                    stance_label TEXT,
                    stance_confidence REAL,
                    sarcasm_probability REAL,
                    topic_terms TEXT NOT NULL DEFAULT '[]',
                    narrative_cluster_id TEXT,
                    trend_score REAL,
                    quality_score REAL,
                    inference_method TEXT,
                    UNIQUE(platform, source_event_id)
                );
                CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);
                CREATE INDEX IF NOT EXISTS idx_events_platform ON events(platform);
                CREATE INDEX IF NOT EXISTS idx_events_narrative ON events(narrative_cluster_id);
                CREATE INDEX IF NOT EXISTS idx_events_raw_hash ON events(raw_hash);
                """
            )

    def reset(self) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM events")

    def _pseudo(self, platform: str, author_platform_id: str | None, author_display: str | None) -> str | None:
        raw = author_platform_id or author_display
        if not raw:
            return None
        token = f"{self.settings.pseudonym_salt}:{platform}:{raw}".encode("utf-8")
        return hashlib.sha256(token).hexdigest()[:16]

    @staticmethod
    def raw_hash(event: SocialEventIn) -> str:
        basis = "|".join(
            [
                event.platform,
                event.source_event_id,
                event.text.strip().lower(),
                event.created_at.astimezone(timezone.utc).isoformat(),
            ]
        )
        return hashlib.sha256(basis.encode("utf-8")).hexdigest()

    def insert(self, event_in: SocialEventIn, derived: dict | None = None) -> SocialEvent | None:
        # Merge first instead of passing overlapping **kwargs. This deliberately
        # lets inference-derived values (e.g. detected language) replace empty
        # normalized fields without triggering duplicate-key TypeErrors.
        event_data = event_in.model_dump()
        event_data.update(derived or {})
        event_data["author_pseudo_id"] = self._pseudo(
            event_in.platform,
            event_in.author_platform_id,
            event_in.author_display,
        )
        event_data["raw_hash"] = self.raw_hash(event_in)
        event = SocialEvent(**event_data)

        payload = event.model_dump(mode="json")
        columns = list(payload.keys())
        values = []
        for key in columns:
            value = payload[key]
            if key in JSON_FIELDS:
                value = json.dumps(value, ensure_ascii=False)
            values.append(value)

        placeholders = ",".join("?" for _ in columns)
        sql = f"INSERT OR IGNORE INTO events ({','.join(columns)}) VALUES ({placeholders})"
        with self.connect() as conn:
            cur = conn.execute(sql, values)
            if cur.rowcount == 0:
                return None
        return event

    def insert_many(self, events: Iterable[tuple[SocialEventIn, dict]]) -> list[SocialEvent]:
        created: list[SocialEvent] = []
        for event, derived in events:
            row = self.insert(event, derived)
            if row is not None:
                created.append(row)
        return created

    def _row_to_event(self, row: sqlite3.Row) -> SocialEvent:
        data = dict(row)
        for key in JSON_FIELDS:
            data[key] = json.loads(data[key] or ("{}" if key in {"engagement", "public_profile", "emotion_scores"} else "[]"))
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["ingested_at"] = datetime.fromisoformat(data["ingested_at"])
        return SocialEvent(**data)

    def list_events(
        self,
        *,
        limit: int = 500,
        platform: str | None = None,
        narrative_id: str | None = None,
        newest_first: bool = False,
    ) -> list[SocialEvent]:
        clauses: list[str] = []
        params: list[object] = []
        if platform:
            clauses.append("platform = ?")
            params.append(platform)
        if narrative_id:
            clauses.append("narrative_cluster_id = ?")
            params.append(narrative_id)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        order = "DESC" if newest_first else "ASC"
        sql = f"SELECT * FROM events{where} ORDER BY created_at {order} LIMIT ?"
        params.append(limit)
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_event(row) for row in rows]

    def get_event(self, event_id: str) -> SocialEvent | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        return self._row_to_event(row) if row else None

    def count(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()
        return int(row["c"])

    def update_derived(self, event_id: str, values: dict) -> None:
        allowed = {
            "sentiment_label",
            "sentiment_score",
            "emotion_scores",
            "stance_label",
            "stance_confidence",
            "sarcasm_probability",
            "topic_terms",
            "narrative_cluster_id",
            "trend_score",
            "quality_score",
            "inference_method",
        }
        clean = {k: v for k, v in values.items() if k in allowed}
        if not clean:
            return
        assignments = []
        params: list[object] = []
        for key, value in clean.items():
            assignments.append(f"{key} = ?")
            if key in JSON_FIELDS:
                value = json.dumps(value, ensure_ascii=False)
            params.append(value)
        params.append(event_id)
        with self.connect() as conn:
            conn.execute(f"UPDATE events SET {', '.join(assignments)} WHERE id = ?", params)


_STORE: EventStore | None = None


def get_store() -> EventStore:
    global _STORE
    if _STORE is None:
        _STORE = EventStore()
    return _STORE
