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
    """Return a continuous, chart-friendly chronology.

    The previous implementation emitted only occupied buckets. A fresh live search
    often places every event in the same 15-minute bucket, which leaves a line
    chart with a single point and therefore no visible line. This version keeps
    truthful counts while padding the observed range with zero-volume buckets so
    the UI always has a readable chronology.
    """
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

    # Add context on both sides. This is a zero-count visual/time-window pad, not
    # synthetic evidence, and keeps a one-bucket workspace visible in Recharts.
    start -= step
    end += step

    # Avoid pathological responses if imported evidence spans years. The API is
    # an analyst visualization, so cap to the most recent 120 buckets.
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


def stable_network(events: list[SocialEvent], narrative_id: str | None = None) -> dict[str, Any]:
    """Build an explainable observed/co-discussion network.

    Strong edges represent replies, mentions, and provider-exposed public follow
    relationships. Lower-weight edges represent shared domains, hashtags, topic
    terms or narrative co-amplification. Co-discussion relationships are never
    presented as proof that two accounts directly interacted.
    """
    chosen = [e for e in events if narrative_id is None or e.narrative_cluster_id == narrative_id]
    graph = nx.DiGraph()
    event_author: dict[str, str] = {}
    handle_to_node: dict[str, str] = {}
    author_events: dict[str, list[SocialEvent]] = defaultdict(list)

    for event in chosen:
        node = event.author_pseudo_id
        if not node:
            continue
        label = event.author_display or f"user-{node[:6]}"
        graph.add_node(node, platform=event.platform, label=label)
        event_author[event.source_event_id] = node
        author_events[node].append(event)
        if event.author_display:
            handle_to_node[event.author_display.lower().lstrip("@")] = node

    def add_edge(source: str, target: str, edge_type: str, weight: float) -> None:
        if not source or not target or source == target:
            return
        if graph.has_edge(source, target):
            graph[source][target]["weight"] += weight
            graph[source][target]["types"].add(edge_type)
        else:
            graph.add_edge(source, target, weight=weight, types={edge_type})

    # Direct observed interactions and provider-reported relationship evidence.
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
            for handle in following[:100]:
                target = handle_to_node.get(str(handle).lower().lstrip("@"))
                if target:
                    add_edge(source, target, "public-follow", 1.15)

    # Low-weight co-discussion relationships. These are deliberately bounded to
    # avoid turning a shared keyword into a strong influence claim.
    nodes = list(author_events)
    for i, source in enumerate(nodes):
        source_events = author_events[source]
        source_domains = {_domain(url) for e in source_events for url in e.urls if url.startswith("http")}
        source_tags = {tag.lower() for e in source_events for tag in e.hashtags}
        source_topics = {term.lower() for e in source_events for term in e.topic_terms}
        source_narratives = {e.narrative_cluster_id for e in source_events if e.narrative_cluster_id}
        for target in nodes[i + 1 :]:
            target_events = author_events[target]
            target_domains = {_domain(url) for e in target_events for url in e.urls if url.startswith("http")}
            target_tags = {tag.lower() for e in target_events for tag in e.hashtags}
            target_topics = {term.lower() for e in target_events for term in e.topic_terms}
            target_narratives = {e.narrative_cluster_id for e in target_events if e.narrative_cluster_id}

            weight = 0.0
            types: list[str] = []
            if source_domains & target_domains:
                weight += 0.55
                types.append("shared-domain")
            if source_tags & target_tags:
                weight += 0.45
                types.append("shared-hashtag")
            if len(source_topics & target_topics) >= 2:
                weight += 0.30
                types.append("shared-topic")
            if source_narratives & target_narratives:
                weight += 0.25
                types.append("narrative-coamplification")

            if weight > 0:
                for edge_type in types:
                    add_edge(source, target, edge_type, weight / len(types))

    if graph.number_of_nodes() == 0:
        return {"nodes": [], "edges": [], "summary": {"nodes": 0, "edges": 0, "communities": 0, "high_reach_nodes": 0, "bridge_nodes": 0}}

    undirected = graph.to_undirected()
    pagerank = nx.pagerank(graph, weight="weight") if graph.number_of_edges() else {n: 0.0 for n in graph.nodes}
    betweenness = nx.betweenness_centrality(undirected, normalized=True) if graph.number_of_nodes() > 2 else {n: 0.0 for n in graph.nodes}
    degree = nx.degree_centrality(undirected) if graph.number_of_nodes() > 1 else {n: 0.0 for n in graph.nodes}

    try:
        communities = list(nx.community.greedy_modularity_communities(undirected, weight="weight")) if graph.number_of_edges() else [{n} for n in graph.nodes]
    except Exception:
        communities = [{n} for n in graph.nodes]
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
        },
    }
