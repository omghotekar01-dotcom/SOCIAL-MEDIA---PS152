from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .advanced_analytics import BIO_INTERESTS, TOKEN_RE, _explicit_age_bracket, _infer_broad_geography, _infer_interest
from .config import get_settings
from .schemas import SocialEvent

SETTINGS = get_settings()


def _behavioral_interest(events: list[SocialEvent]) -> str:
    """Infer a broad professional-interest category from observed public behavior.

    This intentionally targets non-sensitive interest categories only. It does not
    infer age, gender, religion, ethnicity, health, politics, or other protected
    traits from behavior.
    """
    tokens: set[str] = set()
    for event in events:
        tokens.update(str(term).lower() for term in (event.topic_terms or []))
        tokens.update(str(tag).lower() for tag in (event.hashtags or []))
        tokens.update(token.lower().lstrip("#@") for token in TOKEN_RE.findall(event.text or ""))

    best_label = "unknown"
    best_hits = 0
    for label, terms in BIO_INTERESTS.items():
        hits = len(tokens & terms)
        if hits > best_hits:
            best_label = label
            best_hits = hits
    return best_label if best_hits else "unknown"


def ps26152_demographics(events: list[SocialEvent]) -> dict[str, Any]:
    by_user_events: dict[str, list[SocialEvent]] = defaultdict(list)
    for event in events:
        if event.author_pseudo_id:
            by_user_events[event.author_pseudo_id].append(event)

    rows: dict[str, dict[str, str]] = {}
    interest_methods: Counter[str] = Counter()

    for pseudo_id, user_events in by_user_events.items():
        row: dict[str, str] = {}
        for event in user_events:
            profile = event.public_profile or {}
            language = str(profile.get("language") or event.language or "unknown").lower()[:20]
            if row.get("language", "unknown") == "unknown" or language != "unknown":
                row["language"] = language

            geography = _infer_broad_geography(profile)
            if geography != "unknown":
                row["region"] = geography

            profile_interest = _infer_interest(profile)
            if profile_interest != "unknown":
                row["professional_interest"] = profile_interest
                row["professional_interest_method"] = "public-profile/bio"

            age = _explicit_age_bracket(profile)
            if age != "unknown":
                row["age_bracket"] = age

        if row.get("professional_interest", "unknown") == "unknown":
            behavior_interest = _behavioral_interest(user_events)
            if behavior_interest != "unknown":
                row["professional_interest"] = behavior_interest
                row["professional_interest_method"] = "observed-public-topic-behavior"

        interest_methods[row.get("professional_interest_method", "unknown")] += 1
        rows[pseudo_id] = row

    total = len(rows)
    k = SETTINGS.k_anon_min_group

    def aggregate(field: str, method: str) -> dict[str, Any]:
        counts = Counter(row.get(field, "unknown") for row in rows.values())
        suppressed = sum(count for label, count in counts.items() if label != "unknown" and count < k)
        public_counts = {
            label: count
            for label, count in counts.items()
            if label == "unknown" or count >= k
        }
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
            "method": method,
            "known_users": known,
            "unknown_users": counts.get("unknown", 0),
            "suppressed_users": suppressed,
        }

    return {
        "unique_anonymized_users": total,
        "language": aggregate("language", "observed-language-signal"),
        "broad_geography": aggregate("region", "public-location-to-broad-region"),
        "professional_interests": aggregate(
            "professional_interest",
            "public-profile/bio first; broad non-sensitive observed topic behavior fallback",
        ),
        "age_brackets": aggregate("age_bracket", "explicit-self-declared-age-only"),
        "professional_interest_signal_mix": dict(interest_methods),
        "privacy_note": (
            "Aggregate anonymized audience signals only. Small groups are suppressed at k="
            f"{k}. Professional interests may use broad public-topic behavior when profile/bio signals are absent. "
            "Age is never guessed from names, photos or behavior; only explicit self-declared age indicators are used."
        ),
    }
