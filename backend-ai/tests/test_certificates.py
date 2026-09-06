from __future__ import annotations

from datetime import datetime, timezone

from app.analytics import assign_clusters, enrich_event, narrative_summaries, seed_demo_events
from app.certificates import build_narrative_certificate
from app.db import EventStore


def test_demo_narrative_produces_replayable_certificate(tmp_path):
    store = EventStore(tmp_path / 'certificate.db')
    for event in seed_demo_events(datetime(2026, 9, 6, 18, 0, tzinfo=timezone.utc)):
        normalized, derived = enrich_event(event)
        store.insert(normalized, derived)
    assign_clusters(store)

    narratives = narrative_summaries(store)
    assert narratives
    certificate = build_narrative_certificate(store, narratives[0]['id'])
    assert certificate is not None
    assert certificate['decision'] in {'CERTIFIED', 'ABSTAIN'}
    assert len(certificate['integrity']['snapshot_hash_sha256']) == 64
    assert len(certificate['integrity']['algorithm_hash_sha256']) == 64
    assert certificate['replay']['result'] == 'MATCH'
    assert certificate['witness_posts']
    assert certificate['claim']['scope'].startswith('Earliest observed')


def test_missing_narrative_never_gets_certificate(tmp_path):
    store = EventStore(tmp_path / 'empty.db')
    assert build_narrative_certificate(store, 'N-404') is None
