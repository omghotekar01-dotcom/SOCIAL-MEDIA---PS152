from __future__ import annotations

import hashlib

from .analytics import alerts as _raw_alerts
from .db import EventStore
from .schemas import AlertOut


def _stable_alert_id(alert: AlertOut) -> str:
    material = "|".join([
        str(alert.narrative_id),
        alert.triggered_at.isoformat(),
        str(round(float(alert.trend_score), 6)),
        str(alert.title),
    ])
    digest = hashlib.sha256(material.encode("utf-8", errors="ignore")).hexdigest()[:16].upper()
    return f"A-{digest}"


def stable_alerts(store: EventStore) -> list[AlertOut]:
    """Return normal alert analytics with replay-stable identifiers.

    The underlying alert score/reasons remain unchanged. Only the ephemeral UUID
    is replaced with a deterministic ID derived from the narrative + trigger
    state, allowing `/api/alerts` and `/api/certificates/alert/{id}` to refer to
    the same alert across independent API calls.
    """
    output: list[AlertOut] = []
    for alert in _raw_alerts(store):
        output.append(alert.model_copy(update={"alert_id": _stable_alert_id(alert)}))
    return output
