from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from math import sqrt
from typing import Any

from ..schemas import SocialEvent


def _window_count(times: list[datetime], start: datetime, end: datetime) -> int:
    return sum(1 for timestamp in times if start <= timestamp <= end)


def _bucket_counts(times: list[datetime], bucket_minutes: int = 10) -> list[int]:
    if not times:
        return []
    ordered = sorted(times)
    start = ordered[0].replace(second=0, microsecond=0)
    bucket_seconds = bucket_minutes * 60
    counts: dict[int, int] = defaultdict(int)
    for timestamp in ordered:
        offset = max(0, int((timestamp - start).total_seconds()))
        counts[offset // bucket_seconds] += 1
    return [counts[idx] for idx in range(max(counts) + 1)]


def _z_score_latest(buckets: list[int]) -> float:
    if not buckets:
        return 0.0
    latest = buckets[-1]
    history = buckets[:-1]
    if len(history) < 2:
        return float(latest)
    avg = sum(history) / len(history)
    variance = sum((value - avg) ** 2 for value in history) / len(history)
    std = sqrt(variance)
    if std < 0.001:
        return max(0.0, latest - avg)
    return (latest - avg) / std


def compute_trends(events: list[SocialEvent], narratives: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute transparent 20-minute velocity and 10-minute burst statistics."""
    if not events:
        return []

    latest_time = max(event.created_at for event in events)
    by_narrative: dict[str, list[SocialEvent]] = defaultdict(list)
    for event in events:
        if event.narrative_cluster_id:
            by_narrative[event.narrative_cluster_id].append(event)

    narrative_lookup = {item["id"]: item for item in narratives}
    result: list[dict[str, Any]] = []
    for narrative_id, members in by_narrative.items():
        times = sorted(event.created_at for event in members)
        current_start = latest_time - timedelta(minutes=20)
        previous_start = latest_time - timedelta(minutes=40)
        current_count = _window_count(times, current_start, latest_time)
        previous_count = _window_count(times, previous_start, current_start - timedelta(microseconds=1))

        # Laplace smoothing prevents division-by-zero from turning a single event
        # into an infinite-growth alert.
        velocity_ratio = (current_count + 1) / (previous_count + 1)
        acceleration = current_count - previous_count
        buckets = _bucket_counts(times, bucket_minutes=10)
        z_score = _z_score_latest(buckets)

        card = narrative_lookup.get(narrative_id, {})
        platform_diversity = len(card.get("platforms", []))
        cross_platform_bonus = min(0.2, max(0, platform_diversity - 1) * 0.08)
        volume_component = min(1.0, len(members) / 12.0)
        velocity_component = min(1.0, max(0.0, velocity_ratio - 1.0) / 3.0)
        burst_component = min(1.0, max(0.0, z_score) / 4.0)
        trend_score = min(
            1.0,
            0.38 * volume_component
            + 0.34 * velocity_component
            + 0.20 * burst_component
            + cross_platform_bonus,
        )

        if current_count >= 3 and (velocity_ratio >= 1.5 or trend_score >= 0.62):
            status = "RISING"
        elif current_count < previous_count and previous_count >= 2:
            status = "FALLING"
        else:
            status = "STABLE"

        reason_parts = [
            f"{current_count} events in the latest 20-minute window",
            f"{previous_count} events in the preceding window",
            f"velocity ratio {velocity_ratio:.2f}x",
        ]
        if platform_diversity > 1:
            reason_parts.append(f"observed on {platform_diversity} platforms")
        if z_score >= 2:
            reason_parts.append(f"latest 10-minute bucket is {z_score:.1f} standard deviations above prior buckets")

        result.append(
            {
                "narrative_id": narrative_id,
                "title": card.get("title", narrative_id),
                "status": status,
                "mentions": len(members),
                "current_window_mentions": current_count,
                "previous_window_mentions": previous_count,
                "velocity_ratio": round(velocity_ratio, 3),
                "acceleration": acceleration,
                "burst_z_score": round(z_score, 3),
                "trend_score": round(trend_score, 3),
                "platform_diversity": platform_diversity,
                "platform_mix": dict(Counter(event.platform for event in members)),
                "reason": "; ".join(reason_parts),
                "window_end": latest_time.isoformat(),
            }
        )

        for event in members:
            event.trend_score = round(trend_score, 3)

    return sorted(result, key=lambda item: (item["trend_score"], item["mentions"]), reverse=True)


def build_trend_alerts(
    events: list[SocialEvent],
    narratives: list[dict[str, Any]],
    trends: list[dict[str, Any]],
    threshold: float,
) -> list[dict[str, Any]]:
    by_narrative: dict[str, list[SocialEvent]] = defaultdict(list)
    for event in events:
        if event.narrative_cluster_id:
            by_narrative[event.narrative_cluster_id].append(event)
    narrative_lookup = {item["id"]: item for item in narratives}

    alerts: list[dict[str, Any]] = []
    now = max((event.created_at for event in events), default=datetime.now(timezone.utc))
    for trend in trends:
        if trend["trend_score"] < threshold and trend["status"] != "RISING":
            continue
        narrative = narrative_lookup.get(trend["narrative_id"], {})
        reasons = [trend["reason"]]
        if narrative.get("cross_platform"):
            reasons.append(
                "cross-platform migration observed across " + ", ".join(narrative.get("platforms", []))
            )
        if narrative.get("mutation_count", 0) > 0:
            reasons.append(f"{narrative['mutation_count']} wording/semantic mutation points observed")

        member_ids = [event.id for event in sorted(by_narrative[trend["narrative_id"]], key=lambda item: item.created_at)]
        alerts.append(
            {
                "alert_id": f"ALERT-{trend['narrative_id']}",
                "title": "Narrative acceleration detected" if trend["status"] == "RISING" else "High-activity narrative",
                "severity": "HIGH" if trend["trend_score"] >= 0.80 else "MEDIUM",
                "narrative_id": trend["narrative_id"],
                "triggered_at": now.isoformat(),
                "trend_score": trend["trend_score"],
                "why_triggered": reasons,
                "evidence_event_ids": member_ids[-12:],
                "earliest_observed_event_id": narrative.get("earliest_observed_event_id"),
                "platform_mix": trend["platform_mix"],
                "confidence": round(min(0.96, 0.55 + trend["trend_score"] * 0.4), 3),
            }
        )

    return alerts[:25]
