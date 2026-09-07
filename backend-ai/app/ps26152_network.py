from __future__ import annotations

from typing import Any

from .ps26152_intelligence import _link_intelligence
from .stable_views import stable_network


def ps26152_network(events: list[Any], narrative_id: str | None = None) -> dict[str, Any]:
    """Network topology plus explicit influence/spread evidence required by SIH26152."""
    chosen = [event for event in events if narrative_id is None or event.narrative_cluster_id == narrative_id]
    base = stable_network(events, narrative_id)
    enriched = _link_intelligence(chosen, base)
    return {
        **base,
        "edge_type_counts": enriched.get("edge_types", {}),
        "direct_observed_edges": enriched.get("direct_observed_edges", 0),
        "co_discussion_edges": enriched.get("co_discussion_edges", 0),
        "key_opinion_leader_candidates": enriched.get("key_opinion_leader_candidates", []),
        "communities_detail": enriched.get("communities", []),
        "cross_community_flows": enriched.get("cross_community_flows", []),
        "spread_timeline": enriched.get("spread_timeline", []),
        "spread_method_note": enriched.get("method_note", ""),
    }
