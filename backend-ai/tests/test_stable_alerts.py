from __future__ import annotations

from datetime import datetime, timezone

from app.analytics import assign_clusters, enrich_event, seed_demo_events
from app.db import EventStore
from app.stable_alerts import stable_alerts


def test_alert_ids_are_replay_stable(tmp_path):
    store = EventStore(tmp_path / 'alerts.db')
    for event in seed_demo_events(datetime(2026, 9, 6, 18, 0, tzinfo=timezone.utc)):
        normalized, derived = enrich_event(event)
        store.insert(normalized, derived)
    assign_clusters(store)

    first = stable_alerts(store)
    second = stable_alerts(store)

    assert first
    assert [item.alert_id for item in first] == [item.alert_id for item in second]
    assert all(item.alert_id.startswith('A-') for item in first)
    assert all(len(item.alert_id) == 18 for item in first)
