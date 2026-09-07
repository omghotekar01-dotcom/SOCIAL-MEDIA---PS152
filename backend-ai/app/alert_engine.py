from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from .analytics import SETTINGS, build_network, bucket_time, narrative_summaries, trend_metrics
from .db import EventStore
from .schemas import AlertOut, SocialEvent


ALERT_LOOKBACK_BUCKETS = 8
BUCKET_MINUTES = 15


def _qualifies(metrics: dict) -> bool:
    return (
        float(metrics.get("score", 0.0)) >= SETTINGS.nexus_alert_trend_threshold
        or metrics.get("status") in {"RISING", "VIRAL"}
    )


def _recent_peak(
    cluster: list[SocialEvent],
    all_events: list[SocialEvent],
) -> tuple[dict, object, list[SocialEvent]]:
    """Return the strongest recent prefix-level trend state for a narrative.

    Trend cards describe the current/latest bucket. Alerts are different: once a
    narrative crosses the threshold, an analyst must still see that alert even
    if the next bucket cools or contains a correction. We therefore inspect the
    most recent two hours (8 x 15-minute buckets) and retain the strongest
    threshold-crossing state with its actual observation timestamp.
    """
    if not cluster:
        return {"score": 0.0, "status": "STABLE"}, None, []

    ordered_buckets = sorted({bucket_time(event.created_at, BUCKET_MINUTES) for event in cluster})
    candidate_buckets = ordered_buckets[-ALERT_LOOKBACK_BUCKETS:]

    best_metrics: dict | None = None
    best_triggered_at = cluster[-1].created_at
    best_cluster = cluster

    for bucket_start in candidate_buckets:
        bucket_end = bucket_start + timedelta(minutes=BUCKET_MINUTES)
        cluster_prefix = [event for event in cluster if event.created_at < bucket_end]
        if not cluster_prefix:
            continue
        all_prefix = [event for event in all_events if event.created_at < bucket_end]
        metrics = trend_metrics(cluster_prefix, all_prefix or cluster_prefix)
        triggered_at = max(event.created_at for event in cluster_prefix)

        if best_metrics is None or (
            float(metrics.get("score", 0.0)), triggered_at
        ) > (
            float(best_metrics.get("score", 0.0)), best_triggered_at
        ):
            best_metrics = metrics
            best_triggered_at = triggered_at
            best_cluster = cluster_prefix

    return best_metrics or {"score": 0.0, "status": "STABLE"}, best_triggered_at, best_cluster


def persistent_alerts(store: EventStore) -> list[AlertOut]:
    """Generate alerts that remain visible after a recent threshold crossing.

    Current trend status remains untouched in narrative analytics. This alert
    engine only latches a qualifying recent peak, preventing a genuine burst
    from disappearing because the immediately following bucket cooled.
    """
    narratives = narrative_summaries(store)
    all_events = store.list_events(limit=5000)
    network = build_network(all_events)
    top_nodes = network["nodes"][:5]
    output: list[AlertOut] = []

    for narrative in narratives:
        cluster = store.list_events(limit=5000, narrative_id=narrative["id"])
        if not cluster:
            continue

        current = narrative["trend"]
        peak, peak_triggered_at, peak_cluster = _recent_peak(cluster, all_events)

        current_qualifies = _qualifies(current)
        peak_qualifies = _qualifies(peak)
        if not current_qualifies and not peak_qualifies:
            continue

        # Prefer the stronger state. If the current state has cooled, keep the
        # recent crossing and preserve its original trigger timestamp.
        if peak_qualifies and float(peak.get("score", 0.0)) > float(current.get("score", 0.0)):
            trigger = peak
            trigger_cluster = peak_cluster
            triggered_at = peak_triggered_at or cluster[-1].created_at
            latched_from_recent_peak = not current_qualifies or peak.get("status") != current.get("status")
        else:
            trigger = current
            trigger_cluster = cluster
            triggered_at = cluster[-1].created_at
            latched_from_recent_peak = False

        first_half = cluster[: max(1, len(cluster) // 2)]
        second_half = cluster[max(1, len(cluster) // 2) :]
        neg1 = sum(1 for event in first_half if event.sentiment_label == "negative") / max(1, len(first_half))
        neg2 = sum(1 for event in second_half if event.sentiment_label == "negative") / max(1, len(second_half))

        reasons: list[str] = []
        if latched_from_recent_peak:
            reasons.append(
                "Recent peak threshold crossing retained after the latest bucket cooled"
            )
            reasons.append(
                f"Peak trend score {float(trigger['score']):.2f}; current score {float(current['score']):.2f}"
            )
        reasons.extend(
            [
                f"Observed volume growth rate: {float(trigger.get('growth_rate', 0.0)):+.2f}",
                f"Detected across {int(trigger.get('platform_count', 0))} platform(s)",
                f"Unique-author diversity score: {float(trigger.get('author_diversity', 0.0)):.2f}",
            ]
        )
        if neg2 - neg1 >= 0.1:
            reasons.append(f"Negative sentiment increased by {(neg2 - neg1) * 100:.0f} percentage points")

        bridge = next((node for node in top_nodes if node["role"] == "Bridge Node"), None)
        if bridge:
            reasons.append("A bridge node connects otherwise separated observed communities")

        live_platforms = sorted({event.platform for event in cluster if event.source_mode == "LIVE"})
        replay_platforms = sorted({event.platform for event in cluster if event.source_mode != "LIVE"})
        coverage_parts: list[str] = []
        if replay_platforms:
            coverage_parts.append("Replay/import present for: " + ", ".join(replay_platforms))
        if live_platforms:
            coverage_parts.append("Live observed sources: " + ", ".join(live_platforms))

        evidence = trigger_cluster[-min(8, len(trigger_cluster)) :] if trigger_cluster else cluster[-8:]
        trigger_status = str(trigger.get("status", "RISING"))
        trigger_score = float(trigger.get("score", 0.0))

        output.append(
            AlertOut(
                alert_id=f"A-{uuid4().hex[:10]}",
                title=f"{trigger_status} NARRATIVE: {narrative['title']}",
                severity="high" if trigger_status == "VIRAL" else "medium",
                narrative_id=narrative["id"],
                triggered_at=triggered_at,
                trend_score=round(trigger_score, 4),
                why_triggered=reasons,
                evidence_event_ids=[event.id for event in evidence],
                earliest_observed_event_id=cluster[0].id,
                top_amplifiers=[
                    {
                        "pseudo_id": node["id"],
                        "display": node["label"],
                        "role": node["role"],
                        "score": node["pagerank"],
                    }
                    for node in top_nodes[:3]
                ],
                platform_mix=narrative["platform_mix"],
                sentiment_shift={
                    "negative_early": round(neg1, 3),
                    "negative_late": round(neg2, 3),
                },
                coverage_warning=(
                    "; ".join(coverage_parts)
                    if coverage_parts
                    else "Coverage limited to configured connectors and query windows."
                ),
                confidence=round(min(0.94, 0.55 + trigger_score * 0.4), 3),
            )
        )

    return sorted(output, key=lambda alert: (alert.trend_score, alert.triggered_at), reverse=True)
