from __future__ import annotations

from collections import Counter
from typing import Any

from ..config import get_settings
from ..schemas import SocialEvent

INTEREST_KEYWORDS: dict[str, set[str]] = {
    "technology": {"developer", "engineer", "software", "technology", "tech", "data", "ai", "ml", "coding"},
    "education": {"student", "teacher", "professor", "college", "university", "school", "education"},
    "business_finance": {"founder", "business", "finance", "market", "trader", "startup", "investor"},
    "media_journalism": {"journalist", "media", "editor", "reporter", "news", "writer"},
    "public_service": {"government", "public service", "ngo", "volunteer", "civil service", "community"},
    "transport_mobility": {"transport", "metro", "commuter", "mobility", "railway", "traffic"},
}


def _author_key(event: SocialEvent) -> str:
    return event.author_pseudo_id or f"event-author:{event.id}"


def _safe_distribution(counter: Counter[str], total: int, minimum_group: int) -> list[dict[str, Any]]:
    """Return categories with k-anonymous suppression of small groups.

    Small categories are collapsed into `other_or_suppressed`, rather than exposed
    individually. This keeps the dashboard useful while preventing small-group
    disclosure.
    """
    if total < minimum_group:
        return []
    visible: list[tuple[str, int]] = []
    suppressed = 0
    for label, count in counter.most_common():
        if label == "unknown":
            visible.append((label, count))
        elif count >= minimum_group:
            visible.append((label, count))
        else:
            suppressed += count
    if suppressed:
        visible.append(("other_or_suppressed", suppressed))
    return [
        {
            "label": label,
            "count": count,
            "percentage": round(100.0 * count / total, 1) if total else 0.0,
        }
        for label, count in visible
    ]


def aggregate_demographics(events: list[SocialEvent]) -> dict[str, Any]:
    settings = get_settings()
    k = max(2, settings.k_anon_min_group)

    # One public-profile record per pseudonymous author. We intentionally do not
    # merge identities across platforms.
    authors: dict[str, dict[str, Any]] = {}
    author_languages: dict[str, str] = {}
    for event in events:
        key = _author_key(event)
        if key not in authors:
            authors[key] = dict(event.public_profile or {})
            author_languages[key] = event.language or "unknown"
        elif author_languages.get(key) in (None, "unknown") and event.language:
            author_languages[key] = event.language

    total = len(authors)
    language = Counter()
    geography = Counter()
    interests = Counter()
    explicit_age_brackets = Counter()
    known_geo = 0
    known_interest = 0
    known_age = 0

    for key, profile in authors.items():
        language_value = str(profile.get("language") or author_languages.get(key) or "unknown").strip().lower()
        language[language_value or "unknown"] += 1

        # Geography is included only when the public profile explicitly supplies a
        # broad location label. The engine does not infer precise GPS coordinates.
        location = str(profile.get("location") or "").strip()
        if location:
            geography[location] += 1
            known_geo += 1
        else:
            geography["unknown"] += 1

        bio = str(profile.get("bio") or "").lower()
        matched_categories = [
            category
            for category, keywords in INTEREST_KEYWORDS.items()
            if any(keyword in bio for keyword in keywords)
        ]
        if matched_categories:
            known_interest += 1
            for category in matched_categories:
                interests[category] += 1
        else:
            interests["unknown"] += 1

        # We do NOT infer age from language or behavior. A bracket appears only if
        # it was explicitly supplied in authorized/public source data.
        age_bracket = str(profile.get("age_bracket") or "").strip()
        if age_bracket:
            explicit_age_brackets[age_bracket] += 1
            known_age += 1
        else:
            explicit_age_brackets["unknown"] += 1

    publishable = total >= k
    confidence = min(0.95, 0.50 + min(total, 100) / 250.0) if publishable else 0.0

    return {
        "sample_size": total,
        "minimum_publishable_group": k,
        "publishable": publishable,
        "language": _safe_distribution(language, total, k),
        "broad_geography": _safe_distribution(geography, total, k),
        "professional_interests": _safe_distribution(interests, total, k),
        "explicit_age_brackets": _safe_distribution(explicit_age_brackets, total, k),
        "coverage": {
            "language_pct": round(100.0 * sum(count for label, count in language.items() if label != "unknown") / total, 1) if total else 0.0,
            "geography_pct": round(100.0 * known_geo / total, 1) if total else 0.0,
            "professional_interest_pct": round(100.0 * known_interest / total, 1) if total else 0.0,
            "explicit_age_bracket_pct": round(100.0 * known_age / total, 1) if total else 0.0,
        },
        "confidence": round(confidence, 3),
        "privacy_note": (
            "Aggregate, pseudonymous estimates from public/self-declared indicators only. "
            "Small groups are suppressed; sensitive traits are never inferred."
        ),
        "age_note": "Age brackets are shown only when explicitly present in authorized/public source data; NEXUS does not guess an individual's age.",
    }
