from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import networkx as nx
import numpy as np

from .schemas import SocialEvent


def _bucket_time(dt: datetime, minutes: int) -> datetime:
    dt = dt.astimezone(timezone.utc)
    minute = (dt.minute // minutes) * minutes
    return dt.replace(minute=minute, second=0, microsecond=0)


def stable_timeline(events: list[SocialEvent], minutes: int = 15) -> list[dict[str, Any]]:
    """Return a continuous, chart-friendly chronology using every supplied event."""
    if not events:
        return []

    minutes = max(5, min(int(minutes or 15), 120))
    buckets: dict[datetime, list[SocialEvent]] = defaultdict(list)
    for event in events:
        buckets[_bucket_time(event.created_at, minutes)].append(event)

    occupied = sorted(buckets)
    start = occupied[0]
    end = occupied[-1]
    step = timedelta(minutes=minutes)
    start -= step
    end += step

    # Visual cap only: event counts inside the displayed recent buckets remain
    # truthful. This avoids rendering years of empty imported time buckets.
    total_buckets = int((end - start) / step) + 1
    if total_buckets > 120:
        start = end - step * 119

    rows: list[dict[str, Any]] = []
    cursor = start
    while cursor <= end:
        group = buckets.get(cursor, [])
        sentiments = Counter(event.sentiment_label or "unknown" for event in group)
        platforms = Counter(event.platform for event in group)
        rows.append(
            {
                "time": cursor,
                "count": len(group),
                "sentiments": dict(sentiments),
                "platforms": dict(platforms),
            }
        )
        cursor += step
    return rows


def _domain(url: str) -> str:
    return re.sub(r"^https?://", "", url).split("/")[0].lower().removeprefix("www.")


def _unique_nodes(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def stable_network(events: list[SocialEvent], narrative_id: str | None = None) -> dict[str, Any]:
    """Build a scalable observed/co-discussion network.

    Direct evidence (reply, mention, provider-reported public follow) is preserved
    at full strength. Co-discussion relationships use inverted indexes rather than
    O(N^2) all-author comparisons; members of each shared context are linked in a
    deterministic chain with low weight, so every observed participant can remain
    represented without inventing direct interactions.
    """
    chosen = [event for event in events if narrative_id is None or event.narrative_cluster_id == narrative_id]
    graph = nx.DiGraph()
    event_author: dict[str, str] = {}
    handle_to_node: dict[str, str] = {}

    domain_members: dict[str, list[str]] = defaultdict(list)
    hashtag_members: dict[str, list[str]] = defaultdict(list)
    topic_members: dict[str, list[str]] = defaultdict(list)
    narrative_members: dict[str, list[str]] = defaultdict(list)

    for event in chosen:
        node = event.author_pseudo_id
        if not node:
            continue
        label = event.author_display or f"user-{node[:6]}"
        graph.add_node(node, platform=event.platform, label=label)
        event_author[event.source_event_id] = node
        if event.author_display:
            handle_to_node[event.author_display.lower().lstrip("@")] = node

        for url in event.urls:
            if url.startswith("http"):
                domain_members[_domain(url)].append(node)
        for tag in event.hashtags:
            if tag:
                hashtag_members[tag.lower()].append(node)
        for term in event.topic_terms:
            if term:
                topic_members[term.lower()].append(node)
        if event.narrative_cluster_id:
            narrative_members[event.narrative_cluster_id].append(node)

    def add_edge(source: str, target: str, edge_type: str, weight: float) -> None:
        if not source or not target or source == target:
            return
        if graph.has_edge(source, target):
            graph[source][target]["weight"] += weight
            graph[source][target]["types"].add(edge_type)
        else:
            graph.add_edge(source, target, weight=weight, types={edge_type})

    # Direct observed interactions.
    for event in chosen:
        source = event.author_pseudo_id
        if not source:
            continue
        if event.parent_event_id and event.parent_event_id in event_author:
            add_edge(source, event_author[event.parent_event_id], "reply", 2.0)
        for mention in event.mentions:
            target = handle_to_node.get(mention.lower().lstrip("@"))
            if target:
                add_edge(source, target, "mention", 1.5)
        following = (event.public_profile or {}).get("observed_following_handles") or []
        if isinstance(following, list):
            for handle in following[:250]:
                target = handle_to_node.get(str(handle).lower().lstrip("@"))
                if target:
                    add_edge(source, target, "public-follow", 1.15)

    def connect_context(groups: dict[str, list[str]], edge_type: str, weight: float) -> None:
        for members in groups.values():
            unique = _unique_nodes(members)
            if len(unique) < 2:
                continue
            # Chain rather than clique: O(total memberships), not O(group^2).
            for source, target in zip(unique, unique[1:]):
                add_edge(source, target, edge_type, weight)

    connect_context(domain_members, "shared-domain", 0.45)
    connect_context(hashtag_members, "shared-hashtag", 0.35)
    connect_context(topic_members, "shared-topic", 0.16)
    connect_context(narrative_members, "narrative-coamplification", 0.14)

    if graph.number_of_nodes() == 0:
        return {
            "nodes": [],
            "edges": [],
            "summary": {
                "nodes": 0,
                "edges": 0,
                "communities": 0,
                "high_reach_nodes": 0,
                "bridge_nodes": 0,
                "analysis_mode": "empty",
            },
        }

    undirected = graph.to_undirected()
    node_count = graph.number_of_nodes()
    pagerank = nx.pagerank(graph, weight="weight") if graph.number_of_edges() else {node: 0.0 for node in graph.nodes}

    # Exact betweenness becomes expensive on large comment networks. NetworkX's
    # sampled form remains reproducible and preserves structural ranking utility.
    if node_count > 500:
        sample_k = min(200, node_count)
        betweenness = nx.betweenness_centrality(undirected, k=sample_k, normalized=True, seed=42)
        centrality_mode = f"sampled-betweenness-k{sample_k}"
    else:
        betweenness = nx.betweenness_centrality(undirected, normalized=True) if node_count > 2 else {node: 0.0 for node in graph.nodes}
        centrality_mode = "exact-betweenness"

    degree = nx.degree_centrality(undirected) if node_count > 1 else {node: 0.0 for node in graph.nodes}

    try:
        if graph.number_of_edges() and node_count > 800 and hasattr(nx.community, "louvain_communities"):
            communities = list(nx.community.louvain_communities(undirected, weight="weight", seed=42))
            community_mode = "louvain"
        elif graph.number_of_edges():
            communities = list(nx.community.greedy_modularity_communities(undirected, weight="weight"))
            community_mode = "greedy-modularity"
        else:
            communities = [{node} for node in graph.nodes]
            community_mode = "isolated"
    except Exception:
        communities = [{node} for node in graph.nodes]
        community_mode = "fallback-isolated"

    community_by_node = {node: index for index, community in enumerate(communities) for node in community}
    pr_values = list(pagerank.values()) or [0.0]
    reach_threshold = max(0.08, float(np.percentile(pr_values, 75)))

    output_nodes: list[dict[str, Any]] = []
    for node, attrs in graph.nodes(data=True):
        pr = float(pagerank.get(node, 0.0))
        bt = float(betweenness.get(node, 0.0))
        dg = float(degree.get(node, 0.0))
        role = "Bridge Node" if bt >= 0.12 else ("High Reach Node" if pr >= reach_threshold and graph.number_of_edges() else "Participant")
        output_nodes.append(
            {
                "id": node,
                "label": attrs.get("label", node[:6]),
                "platform": attrs.get("platform", "unknown"),
                "pagerank": round(pr, 5),
                "betweenness": round(bt, 5),
                "degree_centrality": round(dg, 5),
                "community": community_by_node.get(node, 0),
                "role": role,
                "explanation": (
                    "Connects otherwise separated communities in the observed/co-discussion graph."
                    if role == "Bridge Node"
                    else "Ranks highly by weighted centrality in the observed/co-discussion graph."
                    if role == "High Reach Node"
                    else "Participates in the observed/co-discussion network."
                ),
            }
        )

    output_nodes.sort(key=lambda item: (item["pagerank"], item["betweenness"], item["degree_centrality"]), reverse=True)
    output_edges = [
        {
            "source": source,
            "target": target,
            "weight": round(float(attrs.get("weight", 1.0)), 3),
            "types": sorted(attrs.get("types", set())),
        }
        for source, target, attrs in graph.edges(data=True)
    ]

    return {
        "nodes": output_nodes,
        "edges": output_edges,
        "summary": {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "communities": len(communities),
            "high_reach_nodes": sum(1 for node in output_nodes if node["role"] == "High Reach Node"),
            "bridge_nodes": sum(1 for node in output_nodes if node["role"] == "Bridge Node"),
            "analysis_mode": f"full-observed-edges + {centrality_mode} + {community_mode}",
            "co_discussion_method": "inverted-context chain; low-weight similarity edges are not direct-interaction claims",
        },
    }
