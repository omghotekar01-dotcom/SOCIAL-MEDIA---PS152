from datetime import datetime, timezone

from app.alert_engine import persistent_alerts
from app.analytics import assign_clusters, enrich_event, seed_demo_events
from app.db import EventStore


def test_recent_peak_alert_survives_correction_cooldown(tmp_path):
    store = EventStore(tmp_path / "latched-alerts.db")
    events = seed_demo_events(datetime(2026, 9, 6, 18, 0, tzinfo=timezone.utc))

    for event in events:
        normalized, derived = enrich_event(event)
        store.insert(normalized, derived)

    assign_clusters(store)
    alerts = persistent_alerts(store)

    assert alerts, "The demo burst must remain alertable after its later correction/cooldown bucket"
    assert all(alert.evidence_event_ids for alert in alerts)
    assert all(alert.triggered_at <= max(event.created_at for event in events) for alert in alerts)
    assert any(
        "threshold crossing" in reason.lower()
        for alert in alerts
        for reason in alert.why_triggered
    ), "At least one demo alert should prove recent-peak latching"
