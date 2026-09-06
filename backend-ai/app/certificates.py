from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from .analytics import build_network, narrative_summaries, trend_metrics
from .config import get_settings
from .db import EventStore
from .schemas import SocialEvent

SETTINGS = get_settings()

ALGORITHM_SPEC = {
    "certificate_schema": "nexus-evidence-certificate-v1",
    "narrative_clustering": "tfidf-cosine+hashtag-url-temporal-graph-v1",
    "sentiment": "vader+transparent-lexical-fallback-v1",
    "network": "networkx-pagerank+betweenness+community-v1",
    "trend": "growth+burst+author-diversity+cross-platform+engagement+recency-v1",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _sha256(value: Any) -> str:
    raw = value if isinstance(value, str) else _canonical_json(value)
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()


def algorithm_hash() -> str:
    return _sha256(
        {
            **ALGORITHM_SPEC,
            "cluster_similarity_threshold": SETTINGS.nexus_cluster_similarity_threshold,
            "alert_trend_threshold": SETTINGS.nexus_alert_trend_threshold,
            "k_anon_min_group": SETTINGS.k_anon_min_group,
        }
    )


def _event_record(event: SocialEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "platform": event.platform,
        "source_mode": event.source_mode,
        "source_event_id": event.source_event_id,
        "created_at": event.created_at.isoformat(),
        "ingested_at": event.ingested_at.isoformat(),
        "author_pseudo_id": event.author_pseudo_id,
        "text": event.text,
        "url": event.url,
        "raw_hash": event.raw_hash,
        "sentiment_label": event.sentiment_label,
        "sentiment_score": event.sentiment_score,
        "stance_label": event.stance_label,
        "narrative_cluster_id": event.narrative_cluster_id,
        "quality_score": event.quality_score,
    }


def _confidence(events: list[SocialEvent], platform_count: int) -> float:
    if not events:
        return 0.0
    quality_values = [float(e.quality_score or 0.0) for e in events]
    quality = sum(quality_values) / max(1, len(quality_values))
    provenance = sum(1 for e in events if e.raw_hash and e.source_event_id and e.created_at) / len(events)
    diversity = min(1.0, len({e.author_pseudo_id for e in events if e.author_pseudo_id}) / 5.0)
    cross_platform = min(1.0, platform_count / 3.0)
    return round(0.35 * quality + 0.30 * provenance + 0.20 * diversity + 0.15 * cross_platform, 4)


def build_narrative_certificate(store: EventStore, narrative_id: str) -> dict[str, Any] | None:
    summaries = {item["id"]: item for item in narrative_summaries(store)}
    summary = summaries.get(narrative_id)
    if not summary:
        return None

    events = sorted(store.list_events(limit=5000, narrative_id=narrative_id), key=lambda e: e.created_at)
    if not events:
        return None

    all_events = store.list_events(limit=5000)
    recomputed_trend = trend_metrics(events, all_events)
    network = build_network(all_events, narrative_id)

    # Preserve the first evidence, then add high-quality/strong-sentiment witnesses.
    witness_candidates = sorted(
        events[1:],
        key=lambda e: (
            float(e.quality_score or 0.0),
            abs(float(e.sentiment_score or 0.0)),
            sum(float(v or 0) for v in e.engagement.values() if isinstance(v, (int, float))),
        ),
        reverse=True,
    )
    witnesses = [events[0], *witness_candidates[:11]]
    witness_records = [_event_record(event) for event in witnesses]
    snapshot_hash = _sha256([_event_record(event) for event in events])
    witness_hash = _sha256(witness_records)
    algo_hash = algorithm_hash()

    author_ids = {event.author_pseudo_id for event in events if event.author_pseudo_id}
    platform_count = len({event.platform for event in events})
    confidence = _confidence(events, platform_count)

    requirements = {
        "minimum_events": len(events) >= 3,
        "minimum_distinct_authors": len(author_ids) >= 2,
        "tamper_evident_raw_hashes": all(bool(event.raw_hash) for event in events),
        "timestamped_evidence": all(bool(event.created_at) for event in events),
        "source_mode_disclosed": all(event.source_mode in {"LIVE", "REPLAY", "IMPORT"} for event in events),
        "confidence_floor": confidence >= 0.50,
    }
    certified = all(requirements.values())

    top_edges = sorted(network.get("edges", []), key=lambda edge: float(edge.get("weight", 0)), reverse=True)[:20]
    top_nodes = sorted(network.get("nodes", []), key=lambda node: float(node.get("pagerank", 0)), reverse=True)[:12]

    replay_payload = {
        "snapshot_hash": snapshot_hash,
        "trend_score": recomputed_trend.get("score", 0.0),
        "trend_status": recomputed_trend.get("status", "STABLE"),
        "network_nodes": network.get("summary", {}).get("nodes", 0),
        "network_edges": network.get("summary", {}).get("edges", 0),
        "algorithm_hash": algo_hash,
    }
    replay_hash = _sha256(replay_payload)

    certificate_core = {
        "schema": ALGORITHM_SPEC["certificate_schema"],
        "narrative_id": narrative_id,
        "snapshot_hash": snapshot_hash,
        "witness_hash": witness_hash,
        "algorithm_hash": algo_hash,
        "thresholds": {
            "cluster_similarity": SETTINGS.nexus_cluster_similarity_threshold,
            "alert_trend": SETTINGS.nexus_alert_trend_threshold,
            "certificate_confidence_floor": 0.50,
        },
        "confidence": confidence,
        "requirements": requirements,
        "replay_hash": replay_hash,
    }
    certificate_id = f"NC-{_sha256(certificate_core)[:20].upper()}"

    return {
        "certificate_id": certificate_id,
        "decision": "CERTIFIED" if certified else "ABSTAIN",
        "abstain_reason": None if certified else [name for name, passed in requirements.items() if not passed],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "claim": {
            "type": "observed_narrative_lineage",
            "narrative_id": narrative_id,
            "title": summary["title"],
            "earliest_observed_at": summary["earliest_observed_at"],
            "earliest_platform": summary["earliest_platform"],
            "event_count": summary["event_count"],
            "platform_mix": summary["platform_mix"],
            "source_modes": summary["source_modes"],
            "scope": "Earliest observed within configured/collected data; not absolute internet origin or actor attribution.",
        },
        "integrity": {
            "snapshot_hash_sha256": snapshot_hash,
            "witness_hash_sha256": witness_hash,
            "algorithm_hash_sha256": algo_hash,
            "certificate_core_hash_sha256": _sha256(certificate_core),
        },
        "thresholds": certificate_core["thresholds"],
        "confidence": confidence,
        "requirements": requirements,
        "witness_posts": witness_records,
        "witness_nodes": top_nodes,
        "witness_edges": top_edges,
        "replay": {
            "result": "MATCH" if _sha256(replay_payload) == replay_hash else "MISMATCH",
            "recomputed": replay_payload,
            "replay_hash_sha256": replay_hash,
        },
        "coverage": {
            "platforms": dict(Counter(event.platform for event in events)),
            "source_modes": dict(Counter(event.source_mode for event in events)),
            "distinct_pseudonymous_authors": len(author_ids),
            "warning": "Coverage is bounded by enabled connectors, permissions, query design, rate limits and platform availability.",
        },
    }


def certificate_summary(certificate: dict[str, Any]) -> dict[str, Any]:
    return {
        "certificate_id": certificate["certificate_id"],
        "decision": certificate["decision"],
        "narrative_id": certificate["claim"]["narrative_id"],
        "confidence": certificate["confidence"],
        "snapshot_hash_sha256": certificate["integrity"]["snapshot_hash_sha256"],
        "algorithm_hash_sha256": certificate["integrity"]["algorithm_hash_sha256"],
        "replay_result": certificate["replay"]["result"],
    }
