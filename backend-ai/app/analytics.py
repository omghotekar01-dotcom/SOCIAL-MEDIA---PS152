from __future__ import annotations

import math
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import networkx as nx
import numpy as np
from langdetect import DetectorFactory, LangDetectException, detect
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from .config import get_settings
from .db import EventStore
from .schemas import AlertOut, SocialEvent, SocialEventIn


DetectorFactory.seed = 42
VADER = SentimentIntensityAnalyzer()
SETTINGS = get_settings()

TOKEN_RE = re.compile(r"[#@]?[\w\-']+", flags=re.UNICODE)
URL_RE = re.compile(r"https?://[^\s]+", flags=re.IGNORECASE)
MENTION_RE = re.compile(r"@([\w_]+)")
HASHTAG_RE = re.compile(r"#([\w_]+)")

STOPWORDS = {
    "the", "a", "an", "and", "or", "is", "are", "was", "were", "to", "of", "in", "on", "for", "with",
    "this", "that", "it", "as", "at", "be", "by", "from", "we", "you", "they", "i", "our", "your", "their",
    "has", "have", "had", "will", "would", "can", "could", "should", "about", "after", "before", "into", "just",
}

EMOTION_LEXICONS = {
    "anxiety": {"worried", "worry", "fear", "afraid", "panic", "unsafe", "uncertain", "concern", "anxious", "risk"},
    "anger": {"angry", "furious", "outrage", "unacceptable", "fail", "failed", "lying", "scam", "hate", "blame"},
    "excitement": {"great", "good", "excellent", "excited", "amazing", "hope", "win", "success", "finally", "love"},
    "sadness": {"sad", "loss", "hurt", "sorry", "disappointed", "disaster", "broken", "regret"},
}

SUPPORT_WORDS = {"support", "agree", "good", "correct", "confirmed", "helpful", "welcome", "trust", "approve", "back"}
AGAINST_WORDS = {"against", "oppose", "wrong", "false", "reject", "boycott", "bad", "fail", "unacceptable", "stop"}
SARCASM_MARKERS = {"yeah right", "surely", "totally believable", "what a surprise", "great job", "nice one"}


def safe_language(text: str, provided: str | None = None) -> str:
    if provided:
        return provided.lower()[:12]
    if not text.strip():
        return "unknown"
    try:
        return detect(text)
    except LangDetectException:
        return "unknown"


def extract_entities(text: str) -> tuple[list[str], list[str], list[str]]:
    return (
        sorted(set(MENTION_RE.findall(text))),
        sorted(set(tag.lower() for tag in HASHTAG_RE.findall(text))),
        sorted(set(URL_RE.findall(text))),
    )


def topic_terms(text: str, top_k: int = 6) -> list[str]:
    words = [
        token.lower().lstrip("#@")
        for token in TOKEN_RE.findall(text)
        if len(token.lstrip("#@")) >= 3 and token.lower().lstrip("#@") not in STOPWORDS
    ]
    counts = Counter(words)
    return [term for term, _ in counts.most_common(top_k)]


def infer_text(text: str, language: str | None = None) -> dict[str, Any]:
    text = " ".join((text or "").split())
    lower = text.lower()
    lang = safe_language(text, language)

    vader = VADER.polarity_scores(text)
    compound = float(vader["compound"])
    if compound >= 0.2:
        sentiment = "positive"
    elif compound <= -0.2:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    tokens = set(word.lower().lstrip("#@") for word in TOKEN_RE.findall(lower))
    support_hits = len(tokens & SUPPORT_WORDS)
    against_hits = len(tokens & AGAINST_WORDS)
    if support_hits > against_hits:
        stance = "supportive"
        stance_conf = min(0.95, 0.55 + 0.1 * support_hits)
    elif against_hits > support_hits:
        stance = "against"
        stance_conf = min(0.95, 0.55 + 0.1 * against_hits)
    else:
        stance = "unclear"
        stance_conf = 0.4

    emotion_raw: dict[str, float] = {}
    total_hits = 0
    for label, lexicon in EMOTION_LEXICONS.items():
        hits = len(tokens & lexicon)
        emotion_raw[label] = float(hits)
        total_hits += hits
    if total_hits == 0:
        emotion_scores = {"neutral_other": 1.0, **{key: 0.0 for key in EMOTION_LEXICONS}}
    else:
        emotion_scores = {key: round(value / total_hits, 3) for key, value in emotion_raw.items()}
        emotion_scores["neutral_other"] = 0.0

    sarcasm = 0.05
    if any(marker in lower for marker in SARCASM_MARKERS):
        sarcasm += 0.45
    if ("!" in text and compound < -0.1 and any(w in tokens for w in {"great", "nice", "amazing"})):
        sarcasm += 0.25
    sarcasm = min(0.9, sarcasm)

    quality = min(1.0, 0.35 + min(len(text), 220) / 440 + (0.1 if lang != "unknown" else 0))

    return {
        "language": lang,
        "sentiment_label": sentiment,
        "sentiment_score": round(compound, 4),
        "emotion_scores": emotion_scores,
        "stance_label": stance,
        "stance_confidence": round(stance_conf, 3),
        "sarcasm_probability": round(sarcasm, 3),
        "topic_terms": topic_terms(text),
        "quality_score": round(quality, 3),
        "inference_method": "vader+transparent-lexical-fallback-v1",
    }


def enrich_event(event: SocialEventIn) -> tuple[SocialEventIn, dict[str, Any]]:
    mentions, hashtags, urls = extract_entities(event.text)
    merged = event.model_copy(
        update={
            "mentions": sorted(set(event.mentions) | set(mentions)),
            "hashtags": sorted(set(event.hashtags) | set(hashtags)),
            "urls": sorted(set(event.urls) | set(urls)),
            "language": safe_language(event.text, event.language),
        }
    )
    return merged, infer_text(merged.text, merged.language)


def bucket_time(dt: datetime, minutes: int = 15) -> datetime:
    dt = dt.astimezone(timezone.utc)
    minute = (dt.minute // minutes) * minutes
    return dt.replace(minute=minute, second=0, microsecond=0)


def cluster_events(events: list[SocialEvent]) -> dict[str, list[SocialEvent]]:
    eligible = [e for e in events if len(e.text.strip()) >= 8]
    if not eligible:
        return {}
    if len(eligible) == 1:
        return {"N-001": eligible}

    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        min_df=1,
        max_features=2500,
        stop_words="english",
    )
    matrix = vectorizer.fit_transform([e.text for e in eligible])
    similarities = cosine_similarity(matrix)

    graph = nx.Graph()
    graph.add_nodes_from(range(len(eligible)))
    threshold = SETTINGS.nexus_cluster_similarity_threshold

    for i in range(len(eligible)):
        for j in range(i + 1, len(eligible)):
            bonus = 0.0
            if set(eligible[i].hashtags) & set(eligible[j].hashtags):
                bonus += 0.12
            if set(eligible[i].urls) & set(eligible[j].urls):
                bonus += 0.18
            delta_hours = abs((eligible[i].created_at - eligible[j].created_at).total_seconds()) / 3600
            time_bonus = 0.05 if delta_hours <= 2 else 0.0
            score = float(similarities[i, j]) + bonus + time_bonus
            if score >= threshold:
                graph.add_edge(i, j, weight=score)

    components = sorted(nx.connected_components(graph), key=lambda comp: min(eligible[idx].created_at for idx in comp))
    clusters: dict[str, list[SocialEvent]] = {}
    for number, component in enumerate(components, start=1):
        label = f"N-{number:03d}"
        clusters[label] = sorted((eligible[idx] for idx in component), key=lambda e: e.created_at)
    return clusters


def assign_clusters(store: EventStore) -> dict[str, list[SocialEvent]]:
    events = store.list_events(limit=5000)
    clusters = cluster_events(events)
    for cluster_id, cluster in clusters.items():
        for event in cluster:
            if event.narrative_cluster_id != cluster_id:
                store.update_derived(event.id, {"narrative_cluster_id": cluster_id})
    return {cluster_id: store.list_events(limit=5000, narrative_id=cluster_id) for cluster_id in clusters}


def _cluster_title(cluster: list[SocialEvent]) -> str:
    terms = Counter(term for e in cluster for term in e.topic_terms)
    if terms:
        top = [t for t, _ in terms.most_common(4)]
        return " / ".join(word.replace("_", " ").title() for word in top)
    first = cluster[0].text if cluster else "Untitled narrative"
    return first[:80] + ("…" if len(first) > 80 else "")


def trend_metrics(cluster: list[SocialEvent], all_events: list[SocialEvent]) -> dict[str, Any]:
    if not cluster:
        return {"score": 0.0, "status": "STABLE"}

    buckets = Counter(bucket_time(e.created_at) for e in cluster)
    ordered_times = sorted(buckets)
    current = buckets[ordered_times[-1]]
    previous_values = [buckets[t] for t in ordered_times[:-1]] or [0]
    baseline = statistics.mean(previous_values)
    growth = (current - baseline) / max(1.0, baseline)

    std = statistics.pstdev(previous_values) if len(previous_values) > 1 else 1.0
    zscore = (current - baseline) / max(1.0, std)
    author_diversity = len({e.author_pseudo_id for e in cluster if e.author_pseudo_id}) / max(1, len(cluster))
    platforms = len({e.platform for e in cluster})
    cross_platform = min(1.0, platforms / 3)

    engagement_now = sum(
        float(e.engagement.get("likes", 0) or 0)
        + float(e.engagement.get("shares", e.engagement.get("reposts", 0)) or 0) * 1.5
        + float(e.engagement.get("replies", e.engagement.get("comments", 0)) or 0)
        for e in cluster[-max(1, len(cluster) // 3) :]
    )
    engagement_norm = min(1.0, math.log1p(engagement_now) / 6)

    age_minutes = max(0.0, (max(e.created_at for e in all_events) - max(e.created_at for e in cluster)).total_seconds() / 60)
    recency = max(0.0, 1.0 - age_minutes / 240)

    normalized_growth = min(1.0, max(0.0, growth / 4))
    normalized_z = min(1.0, max(0.0, zscore / 5))
    score = (
        0.30 * normalized_growth
        + 0.20 * normalized_z
        + 0.15 * author_diversity
        + 0.15 * cross_platform
        + 0.10 * engagement_norm
        + 0.10 * recency
    )
    score = round(float(score), 4)

    if score >= 0.78:
        status = "VIRAL"
    elif score >= 0.58:
        status = "RISING"
    elif score >= 0.38:
        status = "EMERGING"
    elif growth < -0.3:
        status = "DECLINING"
    else:
        status = "STABLE"

    return {
        "score": score,
        "status": status,
        "current_bucket_volume": current,
        "baseline_volume": round(float(baseline), 2),
        "growth_rate": round(float(growth), 3),
        "burst_zscore": round(float(zscore), 3),
        "author_diversity": round(float(author_diversity), 3),
        "platform_count": platforms,
        "engagement_signal": round(float(engagement_norm), 3),
        "recency": round(float(recency), 3),
    }


def narrative_summaries(store: EventStore) -> list[dict[str, Any]]:
    clusters = assign_clusters(store)
    all_events = store.list_events(limit=5000)
    results: list[dict[str, Any]] = []
    for cluster_id, cluster in clusters.items():
        metrics = trend_metrics(cluster, all_events)
        for event in cluster:
            store.update_derived(event.id, {"trend_score": metrics["score"]})
        sentiments = Counter(e.sentiment_label or "unknown" for e in cluster)
        platforms = Counter(e.platform for e in cluster)
        results.append(
            {
                "id": cluster_id,
                "title": _cluster_title(cluster),
                "event_count": len(cluster),
                "earliest_observed_at": cluster[0].created_at,
                "latest_observed_at": cluster[-1].created_at,
                "earliest_event_id": cluster[0].id,
                "earliest_platform": cluster[0].platform,
                "platform_mix": dict(platforms),
                "sentiment_mix": dict(sentiments),
                "trend": metrics,
                "representative_text": cluster[0].text,
                "source_modes": dict(Counter(e.source_mode for e in cluster)),
            }
        )
    results.sort(key=lambda item: (item["trend"]["score"], item["event_count"]), reverse=True)
    return results


def build_network(events: list[SocialEvent], narrative_id: str | None = None) -> dict[str, Any]:
    chosen = [e for e in events if narrative_id is None or e.narrative_cluster_id == narrative_id]
    graph = nx.DiGraph()

    author_lookup: dict[str, str] = {}
    event_author: dict[str, str] = {}
    handle_to_pseudo: dict[str, str] = {}

    for e in chosen:
        if not e.author_pseudo_id:
            continue
        node = e.author_pseudo_id
        author_lookup[node] = e.author_display or f"user-{node[:6]}"
        event_author[e.source_event_id] = node
        if e.author_display:
            handle_to_pseudo[e.author_display.lower().lstrip("@")] = node
        graph.add_node(node, platform=e.platform, label=author_lookup[node])

    def add_edge(source: str, target: str, edge_type: str, weight: float = 1.0):
        if not source or not target or source == target:
            return
        if graph.has_edge(source, target):
            graph[source][target]["weight"] += weight
            graph[source][target]["types"].add(edge_type)
        else:
            graph.add_edge(source, target, weight=weight, types={edge_type})

    domain_authors: dict[str, list[str]] = defaultdict(list)
    cluster_authors: dict[str, list[str]] = defaultdict(list)

    for e in chosen:
        source = e.author_pseudo_id
        if not source:
            continue
        if e.parent_event_id and e.parent_event_id in event_author:
            add_edge(source, event_author[e.parent_event_id], "reply", 1.5)
        for mention in e.mentions:
            target = handle_to_pseudo.get(mention.lower().lstrip("@"))
            if target:
                add_edge(source, target, "mention", 1.0)
        for url in e.urls:
            domain = re.sub(r"^https?://", "", url).split("/")[0].lower()
            domain_authors[domain].append(source)
        if e.narrative_cluster_id:
            cluster_authors[e.narrative_cluster_id].append(source)

    for authors in domain_authors.values():
        unique = list(dict.fromkeys(authors))
        for a, b in zip(unique, unique[1:]):
            add_edge(a, b, "shared-domain", 0.35)

    for authors in cluster_authors.values():
        unique = list(dict.fromkeys(authors))[:60]
        for a, b in zip(unique, unique[1:]):
            add_edge(a, b, "narrative-coamplification", 0.2)

    if graph.number_of_nodes() == 0:
        return {"nodes": [], "edges": [], "summary": {"nodes": 0, "edges": 0}}

    undirected = graph.to_undirected()
    pagerank = nx.pagerank(graph, weight="weight") if graph.number_of_edges() else {n: 0.0 for n in graph.nodes}
    betweenness = nx.betweenness_centrality(undirected, weight=None, normalized=True) if graph.number_of_nodes() > 2 else {n: 0.0 for n in graph.nodes}
    degree = nx.degree_centrality(undirected) if graph.number_of_nodes() > 1 else {n: 0.0 for n in graph.nodes}

    try:
        communities = list(nx.community.greedy_modularity_communities(undirected)) if graph.number_of_edges() else [{n} for n in graph.nodes]
    except Exception:
        communities = [{n} for n in graph.nodes]
    community_by_node = {node: idx for idx, community in enumerate(communities) for node in community}

    nodes = []
    for node, attrs in graph.nodes(data=True):
        pr = float(pagerank.get(node, 0))
        bt = float(betweenness.get(node, 0))
        dg = float(degree.get(node, 0))
        role = "Bridge Node" if bt >= 0.12 else ("High Reach Node" if pr >= max(0.08, np.percentile(list(pagerank.values()), 75)) else "Participant")
        nodes.append(
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
                    "Connects otherwise separated communities in the observed interaction graph."
                    if role == "Bridge Node"
                    else "Ranks highly by weighted interaction centrality in the observed graph."
                    if role == "High Reach Node"
                    else "Participates in the observed narrative network."
                ),
            }
        )

    edges = []
    for source, target, attrs in graph.edges(data=True):
        edges.append(
            {
                "source": source,
                "target": target,
                "weight": round(float(attrs.get("weight", 1.0)), 3),
                "types": sorted(attrs.get("types", [])),
            }
        )

    nodes.sort(key=lambda n: (n["pagerank"], n["betweenness"]), reverse=True)
    return {
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "communities": len(communities),
            "high_reach_nodes": sum(1 for n in nodes if n["role"] == "High Reach Node"),
            "bridge_nodes": sum(1 for n in nodes if n["role"] == "Bridge Node"),
        },
    }


def demographics(events: list[SocialEvent]) -> dict[str, Any]:
    by_user: dict[str, dict[str, Any]] = {}
    for e in events:
        if not e.author_pseudo_id:
            continue
        profile = e.public_profile or {}
        row = by_user.setdefault(e.author_pseudo_id, {"language": e.language or "unknown"})
        row["language"] = profile.get("language") or row.get("language") or "unknown"
        if profile.get("region"):
            row["region"] = profile["region"]
        if profile.get("professional_interest"):
            row["professional_interest"] = profile["professional_interest"]
        if profile.get("age_bracket"):
            row["age_bracket"] = profile["age_bracket"]

    total = len(by_user)
    k = SETTINGS.k_anon_min_group

    def aggregate(field: str) -> dict[str, Any]:
        counts = Counter(str(row.get(field, "unknown")) for row in by_user.values())
        suppressed = sum(count for label, count in counts.items() if label != "unknown" and count < k)
        public_counts = {label: count for label, count in counts.items() if label == "unknown" or count >= k}
        if suppressed:
            public_counts["suppressed_small_groups"] = suppressed
        known = total - counts.get("unknown", 0)
        coverage = known / max(1, total)
        confidence = min(0.95, 0.45 + 0.5 * coverage) if total else 0.0
        return {
            "counts": public_counts,
            "coverage": round(coverage, 3),
            "confidence": round(confidence, 3),
            "minimum_group_size": k,
            "method": "aggregate-public-profile-signals",
        }

    return {
        "unique_anonymized_users": total,
        "language": aggregate("language"),
        "broad_geography": aggregate("region"),
        "professional_interests": aggregate("professional_interest"),
        "age_brackets": aggregate("age_bracket"),
        "privacy_note": "Only aggregate anonymized distributions are returned; small groups are suppressed.",
    }


def timeline(events: list[SocialEvent], minutes: int = 15) -> list[dict[str, Any]]:
    buckets: dict[datetime, list[SocialEvent]] = defaultdict(list)
    for e in events:
        buckets[bucket_time(e.created_at, minutes)].append(e)
    rows = []
    for bucket in sorted(buckets):
        group = buckets[bucket]
        sentiments = Counter(e.sentiment_label or "unknown" for e in group)
        platforms = Counter(e.platform for e in group)
        rows.append(
            {
                "time": bucket,
                "count": len(group),
                "sentiments": dict(sentiments),
                "platforms": dict(platforms),
            }
        )
    return rows


def alerts(store: EventStore) -> list[AlertOut]:
    narratives = narrative_summaries(store)
    all_events = store.list_events(limit=5000)
    network = build_network(all_events)
    top_nodes = network["nodes"][:5]
    output: list[AlertOut] = []

    for narrative in narratives:
        trend = narrative["trend"]
        if trend["score"] < SETTINGS.nexus_alert_trend_threshold and trend["status"] not in {"RISING", "VIRAL"}:
            continue
        cluster = [e for e in store.list_events(limit=5000, narrative_id=narrative["id"])]
        if not cluster:
            continue
        first_half = cluster[: max(1, len(cluster) // 2)]
        second_half = cluster[max(1, len(cluster) // 2) :]
        neg1 = sum(1 for e in first_half if e.sentiment_label == "negative") / max(1, len(first_half))
        neg2 = sum(1 for e in second_half if e.sentiment_label == "negative") / max(1, len(second_half))

        reasons = [
            f"Observed volume growth rate: {trend['growth_rate']:+.2f}",
            f"Detected across {trend['platform_count']} platform(s)",
            f"Unique-author diversity score: {trend['author_diversity']:.2f}",
        ]
        if neg2 - neg1 >= 0.1:
            reasons.append(f"Negative sentiment increased by {(neg2-neg1)*100:.0f} percentage points")
        bridge = next((n for n in top_nodes if n["role"] == "Bridge Node"), None)
        if bridge:
            reasons.append("A bridge node connects otherwise separated observed communities")

        live_platforms = sorted({e.platform for e in cluster if e.source_mode == "LIVE"})
        replay_platforms = sorted({e.platform for e in cluster if e.source_mode != "LIVE"})
        coverage_parts = []
        if replay_platforms:
            coverage_parts.append("Replay/import present for: " + ", ".join(replay_platforms))
        if live_platforms:
            coverage_parts.append("Live observed sources: " + ", ".join(live_platforms))

        output.append(
            AlertOut(
                alert_id=f"A-{uuid4().hex[:10]}",
                title=f"{trend['status']} NARRATIVE: {narrative['title']}",
                severity="high" if trend["status"] == "VIRAL" else "medium",
                narrative_id=narrative["id"],
                triggered_at=cluster[-1].created_at,
                trend_score=trend["score"],
                why_triggered=reasons,
                evidence_event_ids=[e.id for e in cluster[: min(8, len(cluster))]],
                earliest_observed_event_id=cluster[0].id,
                top_amplifiers=[
                    {"pseudo_id": n["id"], "display": n["label"], "role": n["role"], "score": n["pagerank"]}
                    for n in top_nodes[:3]
                ],
                platform_mix=narrative["platform_mix"],
                sentiment_shift={"negative_early": round(neg1, 3), "negative_late": round(neg2, 3)},
                coverage_warning="; ".join(coverage_parts) if coverage_parts else "Coverage limited to configured connectors and query windows.",
                confidence=round(min(0.94, 0.55 + trend["score"] * 0.4), 3),
            )
        )
    return sorted(output, key=lambda a: (a.trend_score, a.triggered_at), reverse=True)


def overview(store: EventStore) -> dict[str, Any]:
    events = store.list_events(limit=5000)
    narratives = narrative_summaries(store) if events else []
    alert_list = alerts(store) if events else []
    sentiments = Counter(e.sentiment_label or "unknown" for e in events)
    platforms = Counter(e.platform for e in events)
    source_modes = Counter(e.source_mode for e in events)
    return {
        "total_events": len(events),
        "platform_mix": dict(platforms),
        "source_modes": dict(source_modes),
        "sentiment_mix": dict(sentiments),
        "active_narratives": len(narratives),
        "rising_narratives": sum(1 for n in narratives if n["trend"]["status"] in {"RISING", "VIRAL"}),
        "alerts": len(alert_list),
        "top_narratives": narratives[:5],
        "latest_event_at": max((e.created_at for e in events), default=None),
        "coverage_note": "All analytics are bounded by configured connector/query coverage. Earliest origin means earliest observed in this dataset.",
    }


def seed_demo_events(now: datetime | None = None) -> list[SocialEventIn]:
    now = (now or datetime.now(timezone.utc)).replace(second=0, microsecond=0)
    base = now - timedelta(hours=3)
    rows: list[SocialEventIn] = []

    users = [f"civic_voice_{i:02d}" for i in range(1, 41)]
    regions = ["West", "West", "Central", "North", "South"]
    interests = ["student", "technology", "local_business", "public_policy", "engineering"]
    languages = ["en", "en", "hi", "mr", "en"]

    def add(
        idx: int,
        platform: str,
        minutes: int,
        text: str,
        author: str,
        *,
        source_mode: str = "REPLAY",
        parent: str | None = None,
        likes: int = 0,
        shares: int = 0,
        topic: str = "river",
    ):
        profile_index = int(re.sub(r"\D", "", author)[-2:] or "1") % len(regions) if any(ch.isdigit() for ch in author) else idx % len(regions)
        rows.append(
            SocialEventIn(
                platform=platform,  # type: ignore[arg-type]
                source_event_id=f"demo-{topic}-{idx:03d}",
                event_type="message" if platform == "telegram" else ("video_comment" if platform == "youtube" else "post"),
                author_platform_id=f"{platform}-{author}",
                author_display=author,
                text=text,
                created_at=base + timedelta(minutes=minutes),
                url=f"https://example.invalid/{platform}/{topic}/{idx}",
                parent_event_id=parent,
                engagement={"likes": likes, "shares": shares, "replies": max(0, shares // 2)},
                public_profile={
                    "language": languages[profile_index],
                    "region": regions[profile_index],
                    "professional_interest": interests[profile_index],
                },
                source_mode=source_mode,  # type: ignore[arg-type]
                connector_run_id="demo-seed-v1",
            )
        )

    # Narrative A — begins quietly, grows rapidly, mutates, then receives a correction.
    seed_texts = [
        "Update: maintenance work is planned on the fictional RiverLink service tonight. #RiverLinkUpdate",
        "Anyone else hearing that RiverLink may have a longer shutdown? #RiverLinkUpdate",
        "Local group says RiverLink maintenance could affect morning service. Concerned about commuters. #RiverLinkUpdate",
        "Unconfirmed: people are saying the whole RiverLink line will stay closed tomorrow. #RiverLinkUpdate",
        "This is worrying. No clear notice yet and people are anxious about tomorrow. #RiverLinkUpdate",
    ]
    for i, text in enumerate(seed_texts, start=1):
        add(i, "telegram" if i <= 3 else "x", i * 18, text, users[i], likes=i * 2, shares=i)

    # Accelerating phase concentrated in the final hour to force a burst signal.
    variants = [
        "RiverLink shutdown tomorrow? This is unacceptable if true. #RiverLinkUpdate",
        "Sharing because commuters need clarity: is RiverLink fully closed or only maintenance blocks? #RiverLinkUpdate",
        "People are worried about RiverLink. Please confirm the actual service window. #RiverLinkUpdate",
        "Yeah right, great job informing everyone at the last minute. #RiverLinkUpdate",
        "RiverLink closure claim is spreading fast across groups. Still no source attached. #RiverLinkUpdate",
        "I oppose spreading an unconfirmed full-shutdown claim. Wait for a verified notice. #RiverLinkUpdate",
        "Can someone verify the RiverLink update? Anxiety is rising in the comments. #RiverLinkUpdate",
        "RiverLink maintenance is real, but a full-day closure has not been confirmed. #RiverLinkUpdate",
    ]
    idx = 10
    for wave in range(4):
        for j, text in enumerate(variants):
            platform = ["x", "telegram", "youtube"][j % 3]
            author = users[(wave * 8 + j + 5) % len(users)]
            suffix = "" if j % 3 else " @civic_voice_07"
            if j % 4 == 0:
                suffix += " https://example.invalid/riverlink-notice"
            add(
                idx,
                platform,
                122 + wave * 10 + j,
                text + suffix,
                author,
                likes=12 + wave * 8 + j * 2,
                shares=3 + wave * 2 + (j % 4),
            )
            idx += 1

    correction_texts = [
        "Confirmed service notice: RiverLink has a limited maintenance block, not a full-day closure. #RiverLinkUpdate",
        "Good to see the exact RiverLink timings published. Please use the verified notice. #RiverLinkUpdate",
        "Correction: earlier full-shutdown messages were wrong. Maintenance is limited to specific hours. #RiverLinkUpdate",
        "Support sharing the verified RiverLink schedule instead of the unconfirmed claim. #RiverLinkUpdate",
    ]
    for j, text in enumerate(correction_texts):
        add(idx, ["telegram", "x", "youtube", "x"][j], 166 + j * 3, text, users[7 + j], likes=30 + j * 7, shares=8 + j, topic="river")
        idx += 1

    # Stable background narrative.
    for j in range(14):
        add(
            200 + j,
            ["x", "telegram", "youtube"][j % 3],
            20 + j * 9,
            f"Registration update for the fictional city TechFest workshop batch {j % 3 + 1}. #TechFestLocal",
            users[(j + 16) % len(users)],
            likes=2 + (j % 4),
            shares=j % 2,
            topic="techfest",
        )

    # Declining background narrative: activity is early, little recent activity.
    for j in range(12):
        add(
            300 + j,
            ["telegram", "x"][j % 2],
            5 + j * 4,
            f"Morning rainfall observation {j + 1}; roads mostly clear in the fictional district. #MonsoonWatchDemo",
            users[(j + 25) % len(users)],
            likes=1,
            shares=0,
            topic="monsoon",
        )

    return rows
