from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from .advanced_analytics import EMOTION_LEXICONS_V2
from .reaction_engine import is_reaction


PLATFORM_REQUIREMENTS: tuple[tuple[str, str, str], ...] = (
    ("x", "ESSENTIAL", "X (formerly Twitter)"),
    ("telegram", "ESSENTIAL", "Telegram"),
    ("instagram", "DESIRABLE", "Instagram"),
    ("facebook", "DESIRABLE", "Facebook"),
    ("reddit", "APPRECIABLE", "Reddit"),
    ("youtube", "APPRECIABLE", "YouTube"),
)


def _bucket(dt: datetime, minutes: int = 15) -> datetime:
    dt = dt.astimezone(timezone.utc)
    minute = (dt.minute // minutes) * minutes
    return dt.replace(minute=minute, second=0, microsecond=0)


def _share(counter: Counter[str], label: str, total: int) -> float:
    return round(counter.get(label, 0) / max(1, total), 4)


def _sentiment_score(label: str | None) -> int:
    return 1 if label == "positive" else -1 if label == "negative" else 0


def _source_coverage(events: list[Any]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    by_platform: dict[str, list[Any]] = defaultdict(list)
    for event in events:
        by_platform[event.platform].append(event)

    for platform, tier, display in PLATFORM_REQUIREMENTS:
        rows = by_platform.get(platform, [])
        roots = [event for event in rows if not is_reaction(event)]
        reactions = [event for event in rows if is_reaction(event)]
        modes = Counter(event.source_mode for event in rows)
        connectors = Counter(
            str((event.public_profile or {}).get("connector") or "unknown")
            for event in rows
        )
        if modes.get("LIVE", 0):
            state = "LIVE_DATA"
        elif rows:
            state = "IMPORT_REPLAY_ONLY"
        else:
            state = "NO_DATA"
        output.append(
            {
                "platform": platform,
                "display": display,
                "tier": tier,
                "state": state,
                "events": len(rows),
                "roots": len(roots),
                "reactions": len(reactions),
                "live": modes.get("LIVE", 0),
                "imported": modes.get("IMPORT", 0),
                "replay": modes.get("REPLAY", 0),
                "connectors": dict(connectors),
                "first_observed_at": min((event.created_at for event in rows), default=None),
                "last_observed_at": max((event.created_at for event in rows), default=None),
            }
        )
    return output


def _sentiment_intelligence(events: list[Any]) -> dict[str, Any]:
    roots = [event for event in events if not is_reaction(event)]
    reactions = [event for event in events if is_reaction(event)]
    sentiment_all = Counter((event.sentiment_label or "unknown") for event in events)
    sentiment_roots = Counter((event.sentiment_label or "unknown") for event in roots)
    sentiment_reactions = Counter((event.sentiment_label or "unknown") for event in reactions)
    stance_reactions = Counter((event.stance_label or "unclear") for event in reactions)

    emotion_totals: Counter[str] = Counter()
    reaction_emotions: Counter[str] = Counter()
    sarcasm_total = 0.0
    reaction_sarcasm = 0.0
    for event in events:
        for label in EMOTION_LEXICONS_V2:
            emotion_totals[label] += float((event.emotion_scores or {}).get(label, 0.0) or 0.0)
        sarcasm_total += float(event.sarcasm_probability or 0.0)
    for event in reactions:
        for label in EMOTION_LEXICONS_V2:
            reaction_emotions[label] += float((event.emotion_scores or {}).get(label, 0.0) or 0.0)
        reaction_sarcasm += float(event.sarcasm_probability or 0.0)

    buckets: dict[datetime, list[Any]] = defaultdict(list)
    for event in events:
        buckets[_bucket(event.created_at)].append(event)

    timeline: list[dict[str, Any]] = []
    for key in sorted(buckets):
        group = buckets[key]
        reaction_group = [event for event in group if is_reaction(event)]
        sentiments = Counter((event.sentiment_label or "unknown") for event in group)
        stances = Counter((event.stance_label or "unclear") for event in reaction_group)
        emotion_means: dict[str, float] = {}
        for label in EMOTION_LEXICONS_V2:
            emotion_means[label] = round(
                sum(float((event.emotion_scores or {}).get(label, 0.0) or 0.0) for event in group) / max(1, len(group)),
                4,
            )
        timeline.append(
            {
                "time": key,
                "events": len(group),
                "reactions": len(reaction_group),
                "sentiment": dict(sentiments),
                "positive_share": _share(sentiments, "positive", len(group)),
                "negative_share": _share(sentiments, "negative", len(group)),
                "supportive_share": _share(stances, "supportive", len(reaction_group)),
                "against_share": _share(stances, "against", len(reaction_group)),
                "sarcasm_mean": round(sum(float(event.sarcasm_probability or 0.0) for event in group) / max(1, len(group)), 4),
                "emotions": emotion_means,
            }
        )

    return {
        "events": len(events),
        "root_events": len(roots),
        "reaction_events": len(reactions),
        "overall_sentiment": dict(sentiment_all),
        "root_sentiment": dict(sentiment_roots),
        "reaction_sentiment": dict(sentiment_reactions),
        "reaction_stance": dict(stance_reactions),
        "emotion_means": {
            label: round(float(emotion_totals[label]) / max(1, len(events)), 4)
            for label in EMOTION_LEXICONS_V2
        },
        "reaction_emotion_means": {
            label: round(float(reaction_emotions[label]) / max(1, len(reactions)), 4)
            for label in EMOTION_LEXICONS_V2
        },
        "sarcasm_mean": round(sarcasm_total / max(1, len(events)), 4),
        "reaction_sarcasm_mean": round(reaction_sarcasm / max(1, len(reactions)), 4),
        "timeline": timeline,
        "method_note": "Hybrid explainable NLP: polarity + eight emotion dimensions + stance + sarcasm. Root content and audience reaction are kept separate.",
    }


def _keyword_intelligence(events: list[Any], latest: datetime | None) -> dict[str, Any]:
    if not events or latest is None:
        return {"window_minutes": 30, "keywords": [], "shifting": []}

    window = timedelta(minutes=30)
    recent_start = latest - window
    previous_start = recent_start - window

    total: Counter[str] = Counter()
    recent: Counter[str] = Counter()
    previous: Counter[str] = Counter()

    for event in events:
        terms = {
            *(str(term).lower().strip() for term in (event.topic_terms or []) if str(term).strip()),
            *(str(tag).lower().strip() for tag in (event.hashtags or []) if str(tag).strip()),
        }
        for term in terms:
            if len(term) < 3:
                continue
            total[term] += 1
            if event.created_at >= recent_start:
                recent[term] += 1
            elif event.created_at >= previous_start:
                previous[term] += 1

    rows: list[dict[str, Any]] = []
    for term, count in total.most_common(40):
        now_count = recent.get(term, 0)
        before_count = previous.get(term, 0)
        delta = now_count - before_count
        growth = round(delta / max(1, before_count), 3)
        predicted = max(0, now_count + delta)
        if now_count >= 5 and growth >= 1.0:
            status = "VIRAL_KEYWORD"
        elif delta >= 2:
            status = "RISING"
        elif delta <= -2:
            status = "FALLING"
        else:
            status = "STABLE"
        rows.append(
            {
                "term": term,
                "total": count,
                "recent": now_count,
                "previous": before_count,
                "delta": delta,
                "growth": growth,
                "predicted_next_window": predicted,
                "status": status,
            }
        )

    rows.sort(key=lambda row: (row["status"] in {"VIRAL_KEYWORD", "RISING"}, row["recent"], row["delta"], row["total"]), reverse=True)
    shifting = sorted(rows, key=lambda row: (abs(row["delta"]), row["recent"], row["total"]), reverse=True)[:10]
    return {
        "window_minutes": 30,
        "keywords": rows[:20],
        "shifting": shifting,
        "scope_note": "Keyword movement compares the latest 30-minute observed window with the preceding 30-minute window in the collected dataset.",
    }


def _link_intelligence(events: list[Any], network: dict[str, Any]) -> dict[str, Any]:
    nodes = list(network.get("nodes") or [])
    edges = list(network.get("edges") or [])
    community_by_node = {str(node.get("id")): int(node.get("community") or 0) for node in nodes}
    node_by_id = {str(node.get("id")): node for node in nodes}

    key_nodes = sorted(
        nodes,
        key=lambda node: (
            float(node.get("pagerank") or 0.0),
            float(node.get("betweenness") or 0.0),
            float(node.get("degree_centrality") or 0.0),
        ),
        reverse=True,
    )[:12]

    edge_types: Counter[str] = Counter()
    cross_flows: dict[tuple[int, int], dict[str, Any]] = {}
    for edge in edges:
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        types = [str(value) for value in (edge.get("types") or [])]
        for edge_type in types:
            edge_types[edge_type] += 1
        source_community = community_by_node.get(source)
        target_community = community_by_node.get(target)
        if source_community is None or target_community is None or source_community == target_community:
            continue
        key = (source_community, target_community)
        row = cross_flows.setdefault(
            key,
            {"source_community": source_community, "target_community": target_community, "weight": 0.0, "edge_count": 0, "types": Counter()},
        )
        row["weight"] += float(edge.get("weight") or 0.0)
        row["edge_count"] += 1
        for edge_type in types:
            row["types"][edge_type] += 1

    event_by_source = {(event.platform, event.source_event_id): event for event in events}
    community_stats: dict[int, dict[str, Any]] = {}
    for event in events:
        node_id = event.author_pseudo_id
        if not node_id or node_id not in community_by_node:
            continue
        community = community_by_node[node_id]
        row = community_stats.setdefault(
            community,
            {
                "community": community,
                "events": 0,
                "authors": set(),
                "first_observed_at": event.created_at,
                "last_observed_at": event.created_at,
                "sentiments": Counter(),
                "stances": Counter(),
                "platforms": Counter(),
            },
        )
        row["events"] += 1
        row["authors"].add(node_id)
        row["first_observed_at"] = min(row["first_observed_at"], event.created_at)
        row["last_observed_at"] = max(row["last_observed_at"], event.created_at)
        row["sentiments"][event.sentiment_label or "unknown"] += 1
        row["stances"][event.stance_label or "unclear"] += 1
        row["platforms"][event.platform] += 1

    communities: list[dict[str, Any]] = []
    for community, row in community_stats.items():
        communities.append(
            {
                "community": community,
                "events": row["events"],
                "authors": len(row["authors"]),
                "first_observed_at": row["first_observed_at"],
                "last_observed_at": row["last_observed_at"],
                "sentiment_mix": dict(row["sentiments"]),
                "stance_mix": dict(row["stances"]),
                "platform_mix": dict(row["platforms"]),
            }
        )
    communities.sort(key=lambda row: (row["first_observed_at"], -row["events"]))

    buckets: dict[datetime, Counter[int]] = defaultdict(Counter)
    sentiment_buckets: dict[datetime, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for event in events:
        node_id = event.author_pseudo_id
        if not node_id or node_id not in community_by_node:
            continue
        community = community_by_node[node_id]
        key = _bucket(event.created_at)
        buckets[key][community] += 1
        sentiment_buckets[key][community] += _sentiment_score(event.sentiment_label)

    spread_timeline = [
        {
            "time": key,
            "communities": {str(community): count for community, count in buckets[key].items()},
            "sentiment_balance": {str(community): score for community, score in sentiment_buckets[key].items()},
        }
        for key in sorted(buckets)
    ]

    direct_types = {"reply", "mention", "public-follow"}
    direct_edges = sum(1 for edge in edges if any(str(edge_type) in direct_types for edge_type in (edge.get("types") or [])))
    inferred_edges = len(edges) - direct_edges

    flows = []
    for row in cross_flows.values():
        flows.append(
            {
                "source_community": row["source_community"],
                "target_community": row["target_community"],
                "weight": round(row["weight"], 3),
                "edge_count": row["edge_count"],
                "types": dict(row["types"]),
            }
        )
    flows.sort(key=lambda row: (row["weight"], row["edge_count"]), reverse=True)

    return {
        "summary": network.get("summary") or {},
        "edge_types": dict(edge_types),
        "direct_observed_edges": direct_edges,
        "co_discussion_edges": inferred_edges,
        "key_opinion_leader_candidates": key_nodes,
        "communities": communities,
        "cross_community_flows": flows[:20],
        "spread_timeline": spread_timeline,
        "method_note": "Influence roles are structural within the observed graph. Cross-community spread is based on timestamped observed/co-discussion relationships and does not imply real-world intent or coordination.",
    }


def build_ps26152_intelligence(store) -> dict[str, Any]:
    """Single audit/intelligence payload covering all five SIH26152 components."""
    from . import analytics

    events = store.list_events(limit=None)
    latest = max((event.created_at for event in events), default=None)
    earliest = min((event.created_at for event in events), default=None)
    roots = [event for event in events if not is_reaction(event)]
    reactions = [event for event in events if is_reaction(event)]

    source_coverage = _source_coverage(events)
    demographics = analytics.demographics(events)
    narratives = analytics.narrative_summaries(store)
    network = analytics.build_network(events)
    sentiment = _sentiment_intelligence(events)
    keywords = _keyword_intelligence(events, latest)
    links = _link_intelligence(events, network)

    essential = [row for row in source_coverage if row["tier"] == "ESSENTIAL"]
    essential_with_data = sum(1 for row in essential if row["events"] > 0)
    essential_live = sum(1 for row in essential if row["live"] > 0)

    known_demo_slices = [
        demographics.get("language", {}).get("coverage", 0),
        demographics.get("broad_geography", {}).get("coverage", 0),
        demographics.get("professional_interests", {}).get("coverage", 0),
        demographics.get("age_brackets", {}).get("coverage", 0),
    ]

    requirements = [
        {
            "id": "A",
            "title": "Continuous Data Collection & Timeline Management",
            "capability": "IMPLEMENTED",
            "workspace_state": "STRONG" if essential_live == len(essential) else "PARTIAL" if essential_with_data else "NO_DATA",
            "evidence": f"{len(events)} timestamped events; {len(reactions)} comments/replies; {essential_with_data}/{len(essential)} essential platforms represented, {essential_live}/{len(essential)} essential platforms LIVE.",
        },
        {
            "id": "B",
            "title": "Multi-Dimensional Sentiment Inference",
            "capability": "IMPLEMENTED",
            "workspace_state": "STRONG" if events and reactions else "PARTIAL" if events else "NO_DATA",
            "evidence": f"{len(EMOTION_LEXICONS_V2)} emotion dimensions + polarity + stance + sarcasm across {len(events)} events; {len(reactions)} audience reactions.",
        },
        {
            "id": "C",
            "title": "Automated Demographic Profiling",
            "capability": "IMPLEMENTED_PRIVACY_SAFE",
            "workspace_state": "STRONG" if max(known_demo_slices or [0]) >= 0.5 else "PARTIAL" if events else "NO_DATA",
            "evidence": f"{demographics.get('unique_anonymized_users', 0)} pseudonymous users; language/geography/interests/age with k-anonymity and explicit coverage.",
        },
        {
            "id": "D",
            "title": "Real-Time Trend & Topic Detection",
            "capability": "IMPLEMENTED",
            "workspace_state": "STRONG" if narratives else "NO_DATA",
            "evidence": f"{len(narratives)} ranked narratives; {len(keywords.get('keywords', []))} tracked keywords with rising/falling movement and next-window estimates.",
        },
        {
            "id": "E",
            "title": "Link Analysis & Network Topology",
            "capability": "IMPLEMENTED",
            "workspace_state": "STRONG" if (network.get('summary') or {}).get('edges', 0) else "PARTIAL" if (network.get('summary') or {}).get('nodes', 0) else "NO_DATA",
            "evidence": f"{(network.get('summary') or {}).get('nodes', 0)} nodes, {(network.get('summary') or {}).get('edges', 0)} edges, {(network.get('summary') or {}).get('communities', 0)} communities with influence and spread analysis.",
        },
    ]

    return {
        "problem_statement": "SIH26152 — Social Media Analytics",
        "organization": "National Technical Research Organisation (NTRO)",
        "generated_at": datetime.now(timezone.utc),
        "requirements": requirements,
        "collection": {
            "events": len(events),
            "roots": len(roots),
            "reactions": len(reactions),
            "first_observed_at": earliest,
            "last_observed_at": latest,
            "historical_span_minutes": round((latest - earliest).total_seconds() / 60, 2) if earliest and latest else 0.0,
            "source_coverage": source_coverage,
            "timeline_storage": "SQLite timestamped historical event store",
            "truth_note": "LIVE / IMPORT / REPLAY are preserved; unavailable providers are not silently simulated.",
        },
        "sentiment": sentiment,
        "demographics": demographics,
        "trends": {
            "narratives": narratives,
            "keywords": keywords,
        },
        "links": links,
    }
