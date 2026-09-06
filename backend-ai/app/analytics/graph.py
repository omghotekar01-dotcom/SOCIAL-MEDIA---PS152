from __future__ import annotations

from collections import defaultdict
from typing import Any

import networkx as nx

from ..schemas import SocialEvent


def _node_id(event: SocialEvent) -> str:
    return event.author_pseudo_id or f"anon:{event.platform}:{event.id[:10]}"


def build_network(events: list[SocialEvent]) -> dict[str, Any]:
    """Build a privacy-aware interaction graph from observed public interactions.

    'Influence' in this module means graph-structural influence within the current
    observed dataset/window. It is never treated as intent, identity, or wrongdoing.
    """
    graph = nx.DiGraph()
    event_lookup: dict[str, SocialEvent] = {}
    source_lookup: dict[str, SocialEvent] = {}
    author_lookup: dict[tuple[str, str], str] = {}

    for event in events:
        node = _node_id(event)
        graph.add_node(
            node,
            label=event.author_display or "Pseudonymous account",
            platform=event.platform,
            source_mode=event.source_mode,
        )
        event_lookup[event.id] = event
        source_lookup[event.source_event_id] = event
        if event.author_platform_id:
            author_lookup[(event.platform, event.author_platform_id.lower().lstrip("@"))] = node

    def add_edge(source: str, target: str, edge_type: str, weight: float = 1.0) -> None:
        if source == target:
            return
        if graph.has_edge(source, target):
            data = graph[source][target]
            data["weight"] = float(data.get("weight", 0.0)) + weight
            types = set(data.get("types", []))
            types.add(edge_type)
            data["types"] = sorted(types)
        else:
            graph.add_edge(source, target, weight=weight, types=[edge_type])

    # Direct reply/repost relationships are strongest evidence of interaction.
    for event in events:
        source_node = _node_id(event)
        parent_key = event.parent_event_id
        if parent_key:
            parent = event_lookup.get(parent_key) or source_lookup.get(parent_key)
            if parent:
                add_edge(source_node, _node_id(parent), "reply_or_repost", 1.8)

        # Resolve mentions only when the mentioned ID maps to an already observed
        # account on the same platform. We do not create external identity profiles.
        for mention in event.mentions:
            target = author_lookup.get((event.platform, mention.lower().lstrip("@")))
            if target:
                add_edge(source_node, target, "mention", 1.0)

    # Shared public URLs and narrative co-membership provide weaker propagation
    # context. We cap link creation to avoid a dense, meaningless clique.
    by_url: dict[str, list[SocialEvent]] = defaultdict(list)
    by_narrative: dict[str, list[SocialEvent]] = defaultdict(list)
    for event in events:
        for url in event.urls[:3]:
            by_url[url].append(event)
        if event.narrative_cluster_id:
            by_narrative[event.narrative_cluster_id].append(event)

    for members in by_url.values():
        ordered = sorted(members, key=lambda event: event.created_at)
        for previous, current in zip(ordered, ordered[1:]):
            add_edge(_node_id(current), _node_id(previous), "shared_url", 0.7)

    for members in by_narrative.values():
        ordered = sorted(members, key=lambda event: event.created_at)
        # Sequential semantic co-membership approximates a possible propagation
        # path without claiming causal transmission.
        for previous, current in zip(ordered, ordered[1:]):
            add_edge(_node_id(current), _node_id(previous), "same_narrative_sequence", 0.35)

    if graph.number_of_nodes() == 0:
        return {
            "nodes": [], "edges": [], "communities": [], "metadata": _metadata(0, 0)
        }

    pagerank = (
        nx.pagerank(graph, weight="weight")
        if graph.number_of_edges()
        else {node: 1.0 / graph.number_of_nodes() for node in graph.nodes}
    )
    undirected = graph.to_undirected()
    betweenness = nx.betweenness_centrality(undirected, normalized=True, weight=None)
    degree = (
        nx.degree_centrality(undirected)
        if graph.number_of_nodes() > 1
        else {node: 0.0 for node in graph.nodes}
    )

    if undirected.number_of_edges():
        raw_communities = list(nx.algorithms.community.greedy_modularity_communities(undirected, weight="weight"))
    else:
        raw_communities = [{node} for node in graph.nodes]
    community_map = {
        node: index + 1
        for index, community in enumerate(raw_communities)
        for node in community
    }

    nodes: list[dict[str, Any]] = []
    for node, attrs in graph.nodes(data=True):
        bridge_score = betweenness.get(node, 0.0) * (1.0 + degree.get(node, 0.0))
        structural_score = (
            0.55 * pagerank.get(node, 0.0)
            + 0.25 * degree.get(node, 0.0)
            + 0.20 * betweenness.get(node, 0.0)
        )
        nodes.append(
            {
                "id": node,
                "label": attrs.get("label") or "Pseudonymous account",
                "platform": attrs.get("platform"),
                "source_mode": attrs.get("source_mode"),
                "community": community_map.get(node),
                "pagerank": round(pagerank.get(node, 0.0), 5),
                "degree_centrality": round(degree.get(node, 0.0), 5),
                "betweenness_centrality": round(betweenness.get(node, 0.0), 5),
                "bridge_score": round(bridge_score, 5),
                "structural_influence_score": round(structural_score, 5),
                "interpretation": "Structural position within observed data only; not a claim about intent or real-world authority.",
            }
        )
    nodes.sort(key=lambda item: (item["structural_influence_score"], item["bridge_score"]), reverse=True)

    edges = [
        {
            "source": source,
            "target": target,
            "weight": round(float(data.get("weight", 1.0)), 3),
            "types": data.get("types", []),
        }
        for source, target, data in graph.edges(data=True)
    ]

    communities = []
    for index, community in enumerate(raw_communities, start=1):
        members = sorted(community)
        platform_mix: dict[str, int] = defaultdict(int)
        for member in members:
            platform_mix[str(graph.nodes[member].get("platform", "unknown"))] += 1
        communities.append(
            {
                "id": index,
                "size": len(members),
                "member_ids": members,
                "platform_mix": dict(platform_mix),
            }
        )

    return {
        "nodes": nodes,
        "edges": edges,
        "communities": communities,
        "top_influence_nodes": nodes[:8],
        "top_bridge_nodes": sorted(nodes, key=lambda item: item["bridge_score"], reverse=True)[:8],
        "metadata": _metadata(graph.number_of_nodes(), graph.number_of_edges()),
    }


def _metadata(nodes: int, edges: int) -> dict[str, Any]:
    return {
        "node_count": nodes,
        "edge_count": edges,
        "meaning": "Observed public interaction topology. Co-narrative sequence edges indicate analytical association, not proven causality.",
    }
