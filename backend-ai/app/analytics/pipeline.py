from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from statistics import mean
from typing import Any

from ..config import get_settings
from ..schemas import SocialEvent
from .demographics import aggregate_demographics
from .evidence import build_evidence_ledger
from .graph import build_network
from .narratives import cluster_events
from .nlp import analyze_text
from .trends import build_trend_alerts, compute_trends


def _quality_score(event: SocialEvent) -> float:
    score = 0.45
    if event.text and len(event.text) >= 20:
        score += 0.12
    if event.created_at:
        score += 0.08
    if event.url:
        score += 0.06
    if event.parent_event_id:
        score += 0.05
    if event.author_pseudo_id:
        score += 0.05
    if event.source_mode == "LIVE":
        score += 0.12
    elif event.source_mode == "IMPORT":
        score += 0.07
    return round(min(0.95, score), 3)


def analyze_events(events: list[SocialEvent]) -> dict[str, Any]:
    """Run the complete deterministic NEXUS analytics pipeline.

    Inputs are copied so API reads do not unexpectedly mutate the persistence
    objects. Live, replay, and imported events use this exact same path.
    """
    working = [event.model_copy(deep=True) for event in events]
    working.sort(key=lambda event: event.created_at)

    for event in working:
        analysis = analyze_text(event.text)
        event.language = event.language or analysis["language"]
        event.sentiment_label = analysis["sentiment_label"]
        event.sentiment_score = analysis["sentiment_score"]
        event.emotion_scores = analysis["emotion_scores"]
        event.stance_label = analysis["stance_label"]
        event.stance_confidence = analysis["stance_confidence"]
        event.sarcasm_probability = analysis["sarcasm_probability"]
        event.topic_terms = analysis["topic_terms"]
        event.inference_method = analysis["inference_method"]
        event.quality_score = _quality_score(event)

    working, narratives = cluster_events(working)
    trends = compute_trends(working, narratives)
    network = build_network(working)
    demographics = aggregate_demographics(working)
    evidence = build_evidence_ledger(working, narratives)
    settings = get_settings()
    alerts = build_trend_alerts(
        working,
        narratives,
        trends,
        threshold=settings.nexus_alert_trend_threshold,
    )
    _enrich_alerts(alerts, working, network, evidence)

    summary = _summary(working, narratives, trends, alerts, evidence)
    platform_timeline = _platform_timeline(working)
    sentiment_timeline = _sentiment_timeline(working)

    return {
        "summary": summary,
        "events": [event.model_dump(mode="json") for event in working],
        "narratives": narratives,
        "trends": trends,
        "network": network,
        "demographics": demographics,
        "evidence": evidence,
        "alerts": alerts,
        "platform_timeline": platform_timeline,
        "sentiment_timeline": sentiment_timeline,
    }


def _summary(
    events: list[SocialEvent],
    narratives: list[dict[str, Any]],
    trends: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    sentiment = Counter(event.sentiment_label or "unknown" for event in events)
    stance = Counter(event.stance_label or "unknown" for event in events)
    emotion = Counter(_dominant_emotion(event) for event in events)
    platforms = Counter(event.platform for event in events)
    modes = Counter(event.source_mode for event in events)
    rising = sum(1 for trend in trends if trend["status"] == "RISING")
    return {
        "events": len(events),
        "unique_authors": len({event.author_pseudo_id for event in events if event.author_pseudo_id}),
        "platforms": dict(platforms),
        "source_modes": dict(modes),
        "narratives": len(narratives),
        "cross_platform_narratives": sum(1 for item in narratives if item.get("cross_platform")),
        "rising_narratives": rising,
        "active_alerts": len(alerts),
        "sentiment": dict(sentiment),
        "stance": dict(stance),
        "emotion": dict(emotion),
        "required_platform_coverage_pct": evidence.get("required_platform_coverage_pct", 0.0),
        "latest_event_at": max((event.created_at for event in events), default=None).isoformat() if events else None,
        "mode_label": _mode_label(events),
    }


def _dominant_emotion(event: SocialEvent) -> str:
    if not event.emotion_scores:
        return "unknown"
    return max(event.emotion_scores.items(), key=lambda item: item[1])[0]


def _mode_label(events: list[SocialEvent]) -> str:
    modes = {event.source_mode for event in events}
    if not modes:
        return "EMPTY"
    if modes == {"LIVE"}:
        return "LIVE"
    if "LIVE" in modes:
        return "MIXED LIVE"
    if modes == {"REPLAY"}:
        return "REPLAY"
    return "IMPORT / REPLAY"


def _platform_timeline(events: list[SocialEvent]) -> list[dict[str, Any]]:
    by_minute: dict[str, Counter[str]] = defaultdict(Counter)
    for event in events:
        key = event.created_at.replace(second=0, microsecond=0).isoformat()
        by_minute[key][event.platform] += 1
    rows = []
    for timestamp in sorted(by_minute):
        row: dict[str, Any] = {"timestamp": timestamp, "total": sum(by_minute[timestamp].values())}
        row.update(by_minute[timestamp])
        rows.append(row)
    return rows


def _sentiment_timeline(events: list[SocialEvent]) -> list[dict[str, Any]]:
    by_minute: dict[str, Counter[str]] = defaultdict(Counter)
    for event in events:
        key = event.created_at.replace(second=0, microsecond=0).isoformat()
        by_minute[key][event.sentiment_label or "unknown"] += 1
    rows = []
    for timestamp in sorted(by_minute):
        row: dict[str, Any] = {"timestamp": timestamp}
        row.update(by_minute[timestamp])
        rows.append(row)
    return rows


def _enrich_alerts(
    alerts: list[dict[str, Any]],
    events: list[SocialEvent],
    network: dict[str, Any],
    evidence: dict[str, Any],
) -> None:
    network_rank = {
        node["id"]: node
        for node in network.get("nodes", [])
    }
    event_lookup = {event.id: event for event in events}

    for alert in alerts:
        member_events = [
            event_lookup[event_id]
            for event_id in alert.get("evidence_event_ids", [])
            if event_id in event_lookup
        ]
        author_nodes = []
        seen = set()
        for event in member_events:
            node_id = event.author_pseudo_id
            if not node_id or node_id in seen or node_id not in network_rank:
                continue
            seen.add(node_id)
            node = network_rank[node_id]
            author_nodes.append(
                {
                    "id": node_id,
                    "label": node.get("label"),
                    "platform": node.get("platform"),
                    "structural_influence_score": node.get("structural_influence_score"),
                    "bridge_score": node.get("bridge_score"),
                }
            )
        author_nodes.sort(key=lambda item: item.get("structural_influence_score") or 0, reverse=True)
        alert["top_amplifiers"] = author_nodes[:5]
        alert["coverage_warning"] = evidence.get("coverage_warning")
        alert["sentiment_shift"] = _alert_sentiment_shift(member_events)


def _alert_sentiment_shift(events: list[SocialEvent]) -> dict[str, Any]:
    if len(events) < 2:
        return {"status": "insufficient", "delta": 0.0}
    ordered = sorted(events, key=lambda event: event.created_at)
    midpoint = max(1, len(ordered) // 2)
    early = ordered[:midpoint]
    late = ordered[midpoint:]

    def avg(items: list[SocialEvent]) -> float:
        values = [float(event.sentiment_score or 0.0) for event in items]
        return mean(values) if values else 0.0

    early_avg, late_avg = avg(early), avg(late)
    delta = late_avg - early_avg
    if delta <= -0.18:
        status = "more_negative"
    elif delta >= 0.18:
        status = "more_positive"
    else:
        status = "stable"
    return {
        "status": status,
        "early_mean_polarity": round(early_avg, 3),
        "late_mean_polarity": round(late_avg, 3),
        "delta": round(delta, 3),
    }
