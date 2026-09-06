from __future__ import annotations

from datetime import datetime, timezone

from app.analytics import (
    assign_clusters,
    build_network,
    demographics,
    enrich_event,
    narrative_summaries,
    seed_demo_events,
)
from app.db import EventStore
from app.schemas import SocialEventIn


def ingest_seed(store: EventStore):
    for event in seed_demo_events(datetime(2026, 9, 6, 18, 0, tzinfo=timezone.utc)):
        normalized, derived = enrich_event(event)
        store.insert(normalized, derived)
    assign_clusters(store)


def test_text_enrichment_extracts_sentiment_and_topics():
    event = SocialEventIn(
        platform="replay",
        source_event_id="1",
        author_display="tester",
        text="This is worrying and unacceptable. #Demo @someone",
        created_at=datetime.now(timezone.utc),
        source_mode="REPLAY",
    )
    normalized, derived = enrich_event(event)
    assert "demo" in normalized.hashtags
    assert "someone" in normalized.mentions
    assert derived["sentiment_label"] in {"negative", "neutral", "positive"}
    assert derived["stance_label"] == "against"
    assert derived["topic_terms"]


def test_store_deduplicates_by_platform_source_id(tmp_path):
    store = EventStore(tmp_path / "test.db")
    event = SocialEventIn(
        platform="replay",
        source_event_id="same-id",
        text="hello world",
        created_at=datetime.now(timezone.utc),
        source_mode="REPLAY",
    )
    normalized, derived = enrich_event(event)
    assert store.insert(normalized, derived) is not None
    assert store.insert(normalized, derived) is None
    assert store.count() == 1


def test_demo_builds_multiple_narratives_and_network(tmp_path):
    store = EventStore(tmp_path / "demo.db")
    ingest_seed(store)
    narratives = narrative_summaries(store)
    assert len(narratives) >= 3
    assert any(item["trend"]["status"] in {"EMERGING", "RISING", "VIRAL"} for item in narratives)

    network = build_network(store.list_events(limit=5000))
    assert network["summary"]["nodes"] > 10
    assert network["summary"]["edges"] > 0


def test_demographics_are_aggregate_only(tmp_path):
    store = EventStore(tmp_path / "demo.db")
    ingest_seed(store)
    result = demographics(store.list_events(limit=5000))
    assert "unique_anonymized_users" in result
    assert "counts" in result["language"]
    assert "privacy_note" in result
    # The API contains aggregate counts, never a per-user demographic map.
    assert "users" not in result
