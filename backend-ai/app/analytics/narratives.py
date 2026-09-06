from __future__ import annotations

from collections import Counter
from datetime import datetime
from hashlib import sha1
from statistics import mean
from typing import Any

from ..config import get_settings
from ..schemas import SocialEvent
from .nlp import cosine, fingerprint, tokens


def _content_terms(text: str) -> set[str]:
    return {t.lstrip("#@") for t in tokens(text) if len(t.lstrip("#@")) >= 3}


def semantic_similarity(a_text: str, b_text: str) -> float:
    """Blend hashed-vector similarity with token overlap.

    The zero-download MVP intentionally uses a deterministic representation. A
    sentence-transformer adapter can later replace `fingerprint` without changing
    the clustering and lineage interfaces.
    """
    vector_score = max(0.0, cosine(fingerprint(a_text), fingerprint(b_text)))
    a_terms, b_terms = _content_terms(a_text), _content_terms(b_text)
    union = a_terms | b_terms
    jaccard = len(a_terms & b_terms) / len(union) if union else 0.0
    # The maximum protects paraphrases that share a strong lexical core while the
    # blend reduces accidental single-token matches.
    blended = 0.72 * vector_score + 0.28 * jaccard
    return round(max(blended, jaccard * 0.82), 4)


def _centroid(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    size = len(vectors[0])
    return [sum(vector[i] for vector in vectors) / len(vectors) for i in range(size)]


def _cluster_id(first_event: SocialEvent, ordinal: int) -> str:
    digest = sha1(f"{first_event.platform}:{first_event.source_event_id}".encode()).hexdigest()[:6].upper()
    return f"N{ordinal:03d}-{digest}"


def cluster_events(events: list[SocialEvent]) -> tuple[list[SocialEvent], list[dict[str, Any]]]:
    """Assign chronological events to semantic narratives and build lineage cards."""
    settings = get_settings()
    threshold = settings.nexus_cluster_similarity_threshold
    ordered = sorted(events, key=lambda event: event.created_at)
    clusters: list[dict[str, Any]] = []

    for event in ordered:
        vector = fingerprint(event.text)
        best_cluster: dict[str, Any] | None = None
        best_score = 0.0

        for cluster in clusters:
            centroid_score = cosine(vector, cluster["centroid"])
            # Compare against recent cluster exemplars as mutations can drift away
            # from the original wording while retaining narrative continuity.
            exemplar_scores = [semantic_similarity(event.text, member.text) for member in cluster["events"][-5:]]
            score = max([centroid_score, *exemplar_scores]) if exemplar_scores else centroid_score
            if score > best_score:
                best_score = score
                best_cluster = cluster

        if best_cluster is None or best_score < threshold:
            narrative_id = _cluster_id(event, len(clusters) + 1)
            event.narrative_cluster_id = narrative_id
            clusters.append(
                {
                    "id": narrative_id,
                    "events": [event],
                    "vectors": [vector],
                    "centroid": vector,
                    "assignment_scores": [1.0],
                }
            )
        else:
            event.narrative_cluster_id = best_cluster["id"]
            best_cluster["events"].append(event)
            best_cluster["vectors"].append(vector)
            best_cluster["assignment_scores"].append(round(best_score, 4))
            best_cluster["centroid"] = _centroid(best_cluster["vectors"])

    cards = [_build_card(cluster) for cluster in clusters]
    cards.sort(key=lambda card: (card["event_count"], card["last_observed"]), reverse=True)
    return ordered, cards


def _build_card(cluster: dict[str, Any]) -> dict[str, Any]:
    events: list[SocialEvent] = sorted(cluster["events"], key=lambda event: event.created_at)
    platforms = sorted({event.platform for event in events})
    term_counts = Counter(term for event in events for term in event.topic_terms)
    sentiment_counts = Counter((event.sentiment_label or "unknown") for event in events)
    stance_counts = Counter((event.stance_label or "unknown") for event in events)

    lineage: list[dict[str, Any]] = []
    mutation_count = 0
    cross_platform_hops = 0
    for previous, current in zip(events, events[1:]):
        score = semantic_similarity(previous.text, current.text)
        cross_platform = previous.platform != current.platform
        mutation = score < 0.72
        mutation_count += int(mutation)
        cross_platform_hops += int(cross_platform)
        lineage.append(
            {
                "from_event_id": previous.id,
                "to_event_id": current.id,
                "from_source_event_id": previous.source_event_id,
                "to_source_event_id": current.source_event_id,
                "from_platform": previous.platform,
                "to_platform": current.platform,
                "semantic_similarity": score,
                "cross_platform": cross_platform,
                "mutation": mutation,
                "elapsed_seconds": max(0, int((current.created_at - previous.created_at).total_seconds())),
            }
        )

    title_terms = [term for term, _ in term_counts.most_common(4)]
    if not title_terms:
        title_terms = _fallback_title(events[0].text)

    confidence_values = [
        value
        for event in events
        for value in (event.sentiment_score, event.stance_confidence)
        if isinstance(value, (float, int))
    ]
    assignment_scores = cluster["assignment_scores"]
    cluster_confidence = mean(assignment_scores) if assignment_scores else 0.0

    return {
        "id": cluster["id"],
        "title": " · ".join(title_terms) if title_terms else "Unlabelled narrative",
        "event_count": len(events),
        "author_count": len({event.author_pseudo_id or event.author_platform_id or event.id for event in events}),
        "origin_platform": events[0].platform,
        "earliest_observed_event_id": events[0].id,
        "earliest_source_event_id": events[0].source_event_id,
        "first_observed": events[0].created_at.isoformat(),
        "last_observed": events[-1].created_at.isoformat(),
        "platforms": platforms,
        "platform_mix": dict(Counter(event.platform for event in events)),
        "source_modes": dict(Counter(event.source_mode for event in events)),
        "cross_platform": len(platforms) > 1,
        "cross_platform_hops": cross_platform_hops,
        "mutation_count": mutation_count,
        "topic_terms": [term for term, _ in term_counts.most_common(12)],
        "sentiment_distribution": dict(sentiment_counts),
        "stance_distribution": dict(stance_counts),
        "cluster_confidence": round(float(cluster_confidence), 3),
        "analysis_confidence_hint": round(mean(confidence_values), 3) if confidence_values else None,
        "sample_text": events[0].text,
        "event_ids": [event.id for event in events],
        "lineage": lineage,
    }


def _fallback_title(text: str) -> list[str]:
    terms: list[str] = []
    for term in _content_terms(text):
        terms.append(term)
        if len(terms) == 4:
            break
    return sorted(terms)


def narrative_events(events: list[SocialEvent], narrative_id: str) -> list[SocialEvent]:
    return sorted(
        [event for event in events if event.narrative_cluster_id == narrative_id],
        key=lambda event: event.created_at,
    )
