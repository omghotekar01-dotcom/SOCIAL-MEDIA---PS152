from __future__ import annotations

import hashlib
from collections import Counter

from .db import EventStore
from .reaction_engine import is_reaction, summarize_conversation
from .schemas import AlertOut
from .stable_alerts import stable_alerts


def _reaction_alert_id(narrative_id: str, root_id: str, risk_score: int) -> str:
    material = f"reaction|{narrative_id}|{root_id}|{risk_score}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16].upper()
    return f"A-RX-{digest}"


def complete_alerts(store: EventStore) -> list[AlertOut]:
    """Combine trend alerts with evidence-bounded audience-reaction attention alerts.

    Reaction alerts describe captured comments/replies only. They never classify a
    person or post as malicious, guilty, dangerous, or wrong; the alert simply
    surfaces a rapidly negative/polarized reaction environment for analyst review.
    """
    base = stable_alerts(store)
    events = store.list_events(limit=5000)
    by_narrative = {alert.narrative_id: alert for alert in base}
    output = list(base)

    roots = [event for event in events if not is_reaction(event)]
    for root in roots:
        if not root.narrative_cluster_id:
            continue
        summary = summarize_conversation(root, events)
        reaction_count = int(summary["reaction_count"])
        risk_score = int(summary["risk_score"])
        if reaction_count < 3 or risk_score < 35:
            continue

        negative = float(summary["negative_share"])
        against = float(summary["against_share"])
        flags = list(summary.get("flags") or [])
        reasons = [
            f"Captured audience replies/comments: {reaction_count}",
            f"Negative audience reaction: {negative * 100:.0f}%",
            f"Against stance in captured reactions: {against * 100:.0f}%",
            f"Reaction attention score: {risk_score}/100 ({summary['risk_label']})",
        ]
        if flags:
            reasons.append("Observed reaction indicators: " + ", ".join(flag.replace("-", " ") for flag in flags[:4]))

        existing = by_narrative.get(root.narrative_cluster_id)
        if existing:
            merged_reasons = list(dict.fromkeys([*existing.why_triggered, *reasons]))
            severity = "high" if risk_score >= 60 or existing.severity == "high" else existing.severity
            evidence_ids = list(dict.fromkeys([
                *existing.evidence_event_ids,
                root.id,
                *[sample["event_id"] for sample in summary.get("sample_reactions", [])],
            ]))[:12]
            updated = existing.model_copy(
                update={
                    "why_triggered": merged_reasons,
                    "severity": severity,
                    "evidence_event_ids": evidence_ids,
                    "sentiment_shift": {
                        **existing.sentiment_shift,
                        "audience_negative": round(negative, 3),
                        "audience_against": round(against, 3),
                        "reaction_risk": risk_score / 100,
                    },
                    "confidence": round(min(0.97, max(existing.confidence, float(summary["confidence"]))), 3),
                }
            )
            output = [updated if alert.alert_id == existing.alert_id else alert for alert in output]
            by_narrative[root.narrative_cluster_id] = updated
            continue

        cluster = [event for event in events if event.narrative_cluster_id == root.narrative_cluster_id]
        platform_mix = dict(Counter(event.platform for event in cluster))
        evidence_ids = [root.id, *[sample["event_id"] for sample in summary.get("sample_reactions", [])]][:12]
        live = sorted({event.platform for event in cluster if event.source_mode == "LIVE"})
        imported = sorted({event.platform for event in cluster if event.source_mode != "LIVE"})
        coverage = []
        if live:
            coverage.append("Live observed sources: " + ", ".join(live))
        if imported:
            coverage.append("Replay/import present for: " + ", ".join(imported))
        coverage.append("Reaction signal is bounded to captured replies/comments; it is not a wrongdoing or intent assessment.")

        alert = AlertOut(
            alert_id=_reaction_alert_id(root.narrative_cluster_id, root.id, risk_score),
            title=f"AUDIENCE REACTION {summary['risk_label']}: {root.narrative_cluster_id}",
            severity="high" if risk_score >= 60 else "medium",
            narrative_id=root.narrative_cluster_id,
            triggered_at=max((event.created_at for event in cluster), default=root.created_at),
            trend_score=round(float(root.trend_score or 0.0), 4),
            why_triggered=reasons,
            evidence_event_ids=evidence_ids,
            earliest_observed_event_id=min(cluster, key=lambda event: event.created_at).id if cluster else root.id,
            top_amplifiers=[],
            platform_mix=platform_mix,
            sentiment_shift={
                "audience_negative": round(negative, 3),
                "audience_against": round(against, 3),
                "reaction_risk": risk_score / 100,
            },
            coverage_warning="; ".join(coverage),
            confidence=round(float(summary["confidence"]), 3),
        )
        output.append(alert)
        by_narrative[root.narrative_cluster_id] = alert

    return sorted(output, key=lambda alert: (alert.severity == "high", alert.trend_score, alert.triggered_at), reverse=True)
