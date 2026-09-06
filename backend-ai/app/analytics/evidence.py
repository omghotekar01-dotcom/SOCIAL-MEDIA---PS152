from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from ..schemas import SocialEvent

REQUIRED_PLATFORMS = ("x", "telegram")
OPTIONAL_PLATFORMS = ("instagram", "facebook", "youtube", "reddit")


def _event_confidence(event: SocialEvent) -> float:
    values: list[float] = []
    if event.stance_confidence is not None:
        values.append(max(0.0, min(1.0, float(event.stance_confidence))))
    # VADER's sentiment score is polarity, not confidence. Convert its magnitude
    # into a conservative confidence hint without conflating sign and confidence.
    if event.sentiment_score is not None:
        values.append(min(1.0, 0.5 + abs(float(event.sentiment_score)) * 0.45))
    if event.quality_score is not None:
        values.append(max(0.0, min(1.0, float(event.quality_score))))
    return mean(values) if values else 0.5


def build_evidence_ledger(
    events: list[SocialEvent],
    narratives: list[dict[str, Any]],
) -> dict[str, Any]:
    observed_platforms = sorted({event.platform for event in events if event.platform != "replay"})
    source_modes = Counter(event.source_mode for event in events)
    latest_ingest = max((event.ingested_at for event in events), default=None)
    earliest_source_time = min((event.created_at for event in events), default=None)
    latest_source_time = max((event.created_at for event in events), default=None)
    confidence_values = [_event_confidence(event) for event in events]

    now = datetime.now(timezone.utc)
    freshness_seconds = None
    if latest_ingest:
        parsed = latest_ingest
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        freshness_seconds = max(0, int((now - parsed.astimezone(timezone.utc)).total_seconds()))

    required_present = [platform for platform in REQUIRED_PLATFORMS if platform in observed_platforms]
    required_missing = [platform for platform in REQUIRED_PLATFORMS if platform not in observed_platforms]
    coverage_ratio = len(required_present) / len(REQUIRED_PLATFORMS)

    narrative_ledgers = [
        narrative_evidence(events, narrative)
        for narrative in narratives
    ]

    return {
        "event_count": len(events),
        "unique_pseudonymous_authors": len({event.author_pseudo_id for event in events if event.author_pseudo_id}),
        "observed_platforms": observed_platforms,
        "required_platforms": list(REQUIRED_PLATFORMS),
        "required_platforms_present": required_present,
        "missing_required_platforms": required_missing,
        "optional_platforms_present": [platform for platform in OPTIONAL_PLATFORMS if platform in observed_platforms],
        "required_platform_coverage_pct": round(coverage_ratio * 100.0, 1),
        "source_modes": dict(source_modes),
        "earliest_source_time": earliest_source_time.isoformat() if earliest_source_time else None,
        "latest_source_time": latest_source_time.isoformat() if latest_source_time else None,
        "latest_ingest_time": latest_ingest.isoformat() if latest_ingest else None,
        "ingest_freshness_seconds": freshness_seconds,
        "mean_analysis_confidence": round(mean(confidence_values), 3) if confidence_values else 0.0,
        "narratives": narrative_ledgers,
        "coverage_warning": (
            "Required X and Telegram are both represented in the observed dataset."
            if not required_missing
            else "Coverage is incomplete: missing " + ", ".join(required_missing) + ". Analytical conclusions apply only to observed sources."
        ),
        "truthfulness_note": (
            "NEXUS does not treat social-media repetition as proof. Credibility states describe evidence coverage/corroboration, "
            "not an absolute declaration that a claim is true or false."
        ),
    }


def narrative_evidence(events: list[SocialEvent], narrative: dict[str, Any]) -> dict[str, Any]:
    member_ids = set(narrative.get("event_ids", []))
    members = [event for event in events if event.id in member_ids]
    platforms = sorted({event.platform for event in members})
    modes = sorted({event.source_mode for event in members})

    # Authoritative corroboration is only recognized if a connector/import explicitly
    # tags a public profile/source as authoritative. It is never guessed from follower
    # count or popularity.
    authoritative_members = [
        event for event in members
        if bool((event.public_profile or {}).get("authoritative_source"))
    ]

    stance_labels = Counter(event.stance_label or "unknown" for event in members)
    has_support = stance_labels.get("supportive", 0) > 0
    has_against = stance_labels.get("against", 0) > 0
    if authoritative_members:
        state = "corroborated"
        state_reason = "At least one observed source is explicitly tagged as authoritative in authorized/public metadata."
    elif has_support and has_against and len(members) >= 3:
        state = "conflicting evidence"
        state_reason = "Observed posts contain materially different stance signals; analyst verification is required."
    elif len(platforms) >= 2 and len(members) >= 3:
        state = "uncorroborated"
        state_reason = "The narrative is observed across multiple platforms, but no authoritative evidence source is attached."
    else:
        state = "insufficient evidence"
        state_reason = "Observed evidence is too limited to characterize corroboration beyond this dataset."

    confidences = [_event_confidence(event) for event in members]
    return {
        "narrative_id": narrative.get("id"),
        "credibility_state": state,
        "state_reason": state_reason,
        "event_count": len(members),
        "platforms": platforms,
        "source_modes": modes,
        "authoritative_source_count": len(authoritative_members),
        "mean_analysis_confidence": round(mean(confidences), 3) if confidences else 0.0,
        "earliest_observed_event_id": narrative.get("earliest_observed_event_id"),
        "first_observed": narrative.get("first_observed"),
        "last_observed": narrative.get("last_observed"),
        "scope_note": "State refers to observed evidence coverage, not universal truth.",
    }
