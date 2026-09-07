from __future__ import annotations

from collections import Counter
from typing import Any


def complete_narrative_summaries(store) -> list[dict[str, Any]]:
    """Build narrative/trend summaries from the full active workspace.

    Root clustering is handled by the scalable conversation-aware assigner. Once
    reactions inherit a narrative id, every captured comment/reply contributes to
    narrative event counts, sentiment distribution and trend metrics.
    """
    from . import analytics

    clusters = analytics.assign_clusters(store)
    all_events = store.list_events(limit=None)
    results: list[dict[str, Any]] = []

    for cluster_id, cluster in clusters.items():
        if not cluster:
            continue
        metrics = analytics.trend_metrics(cluster, all_events)
        for event in cluster:
            store.update_derived(event.id, {"trend_score": metrics["score"]})
        sentiments = Counter(event.sentiment_label or "unknown" for event in cluster)
        platforms = Counter(event.platform for event in cluster)
        results.append(
            {
                "id": cluster_id,
                "title": analytics._cluster_title(cluster),
                "event_count": len(cluster),
                "earliest_observed_at": cluster[0].created_at,
                "latest_observed_at": cluster[-1].created_at,
                "earliest_event_id": cluster[0].id,
                "earliest_platform": cluster[0].platform,
                "platform_mix": dict(platforms),
                "sentiment_mix": dict(sentiments),
                "trend": metrics,
                "representative_text": cluster[0].text,
                "source_modes": dict(Counter(event.source_mode for event in cluster)),
                "analytics_population": "all events assigned to this narrative in the active workspace",
            }
        )

    results.sort(key=lambda item: (item["trend"]["score"], item["event_count"]), reverse=True)
    return results
