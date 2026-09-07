from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from .analytics import demographics as _base_demographics
from .analytics import infer_text as _base_infer_text
from .analytics import overview as _base_overview
from .analytics import trend_metrics as _base_trend_metrics
from .config import get_settings
from .reaction_engine import workspace_reaction_overview
from .schemas import SocialEvent

SETTINGS = get_settings()

TOKEN_RE = re.compile(r"[#@]?[\w\-']+", flags=re.UNICODE)

# Eight explicit emotion dimensions. Sarcasm and supportive/against remain
# separate signals because the SIH problem statement treats them as distinct
# nuances rather than ordinary emotions.
EMOTION_LEXICONS_V2: dict[str, set[str]] = {
    "anxiety": {"worried", "worry", "fear", "afraid", "panic", "unsafe", "uncertain", "concern", "concerned", "anxious", "risk", "nervous", "scared", "doubt"},
    "anger": {"angry", "furious", "outrage", "outraged", "unacceptable", "hate", "blame", "rage", "annoyed", "mad", "betrayal", "liar", "lying"},
    "excitement": {"excited", "amazing", "awesome", "wow", "finally", "viral", "hype", "thrilled", "incredible", "fantastic", "win", "winning"},
    "sadness": {"sad", "loss", "hurt", "sorry", "disappointed", "disaster", "broken", "regret", "tragic", "cry", "grief", "upset"},
    "joy": {"happy", "love", "great", "good", "beautiful", "delight", "glad", "smile", "fun", "enjoy", "celebrate", "wonderful"},
    "disgust": {"disgusting", "gross", "shameful", "nasty", "sickening", "repulsive", "filthy", "awful", "pathetic", "toxic"},
    "surprise": {"surprised", "surprise", "shocked", "unexpected", "unbelievable", "seriously", "what", "suddenly", "stunned", "wild"},
    "trust": {"trust", "trusted", "credible", "verified", "confirmed", "reliable", "authentic", "legit", "transparent", "evidence", "proof"},
}

BIO_INTERESTS: dict[str, set[str]] = {
    "technology": {"developer", "engineer", "engineering", "coding", "programmer", "software", "ai", "ml", "data", "cyber", "tech"},
    "education_student": {"student", "college", "university", "teacher", "professor", "researcher", "research", "education", "learner"},
    "business_entrepreneurship": {"business", "founder", "startup", "entrepreneur", "marketing", "sales", "commerce", "brand"},
    "media_creative": {"journalist", "media", "creator", "artist", "designer", "photographer", "writer", "music", "film"},
    "healthcare": {"doctor", "nurse", "health", "medical", "medicine", "hospital", "pharma", "fitness"},
    "public_policy": {"policy", "government", "civil", "law", "legal", "public", "ngo", "social", "politics"},
    "finance": {"finance", "banking", "investor", "investment", "trader", "economics", "accounting", "fintech"},
    "sports": {"sports", "cricket", "football", "athlete", "fitness", "coach", "running"},
}

GEO_GROUPS: dict[str, set[str]] = {
    "West India": {"maharashtra", "pune", "mumbai", "nashik", "goa", "gujarat", "ahmedabad", "rajasthan", "jaipur"},
    "North India": {"delhi", "new delhi", "punjab", "chandigarh", "haryana", "uttar pradesh", "uttarakhand", "himachal", "jammu", "kashmir"},
    "South India": {"karnataka", "bengaluru", "bangalore", "kerala", "tamil nadu", "chennai", "telangana", "hyderabad", "andhra"},
    "East India": {"west bengal", "kolkata", "odisha", "bihar", "jharkhand"},
    "Central India": {"madhya pradesh", "bhopal", "indore", "chhattisgarh", "raipur"},
    "North-East India": {"assam", "guwahati", "meghalaya", "manipur", "mizoram", "nagaland", "tripura", "sikkim", "arunachal"},
}


def advanced_infer_text(text: str, language: str | None = None) -> dict[str, Any]:
    result = _base_infer_text(text, language)
    normalized = " ".join((text or "").split())
    tokens = {token.lower().lstrip("#@") for token in TOKEN_RE.findall(normalized)}

    raw: dict[str, float] = {}
    total_hits = 0.0
    for label, lexicon in EMOTION_LEXICONS_V2.items():
        hits = float(len(tokens & lexicon))
        raw[label] = hits
        total_hits += hits

    # VADER adds a small affect prior so ordinary positive/negative language still
    # contributes when it does not contain one of the transparent lexicon words.
    sentiment = result.get("sentiment_label")
    compound = float(result.get("sentiment_score") or 0)
    if sentiment == "positive" and total_hits == 0:
        raw["joy"] += min(1.0, max(0.2, abs(compound)))
        total_hits += raw["joy"]
    elif sentiment == "negative" and total_hits == 0:
        raw["anxiety"] += min(0.6, max(0.2, abs(compound) * 0.6))
        raw["sadness"] += min(0.4, max(0.1, abs(compound) * 0.4))
        total_hits += raw["anxiety"] + raw["sadness"]

    if total_hits <= 0:
        emotion_scores = {label: 0.0 for label in EMOTION_LEXICONS_V2}
        emotion_scores["neutral_other"] = 1.0
    else:
        emotion_scores = {label: round(value / total_hits, 3) for label, value in raw.items()}
        emotion_scores["neutral_other"] = 0.0

    result["emotion_scores"] = emotion_scores
    result["inference_method"] = "vader+8emotion-lexicon+stance+sarcasm-v2"
    return result


def _infer_interest(profile: dict[str, Any]) -> str:
    explicit = str(profile.get("professional_interest") or "").strip()
    if explicit:
        return explicit.lower().replace(" ", "_")[:80]
    bio = " ".join(str(profile.get(key) or "") for key in ("bio", "description", "headline")).lower()
    tokens = {token.lower() for token in TOKEN_RE.findall(bio)}
    best_label = "unknown"
    best_hits = 0
    for label, terms in BIO_INTERESTS.items():
        hits = len(tokens & terms)
        if hits > best_hits:
            best_label, best_hits = label, hits
    return best_label if best_hits else "unknown"


def _infer_broad_geography(profile: dict[str, Any]) -> str:
    explicit = str(profile.get("broad_geography") or "").strip()
    if explicit:
        return explicit[:80]
    raw = str(profile.get("region") or profile.get("location") or "").lower().strip()
    if not raw:
        return "unknown"
    for label, terms in GEO_GROUPS.items():
        if any(term in raw for term in terms):
            return label
    # Do not expose a rare free-form location as a demographic bucket. It would
    # undermine k-anonymity and can be misleading. Keep only a broad disclosure.
    if "india" in raw:
        return "India (other/unspecified)"
    return "Other public location"


def _explicit_age_bracket(profile: dict[str, Any]) -> str:
    explicit = str(profile.get("age_bracket") or "").strip()
    if explicit:
        return explicit[:40]
    bio = " ".join(str(profile.get(key) or "") for key in ("bio", "description", "headline"))
    match = re.search(r"\b(?:age\s*[:=-]?\s*|i\s*am\s+|i['’]?m\s+)(1[3-9]|[2-7]\d|8[0-9])\b", bio, flags=re.I)
    if not match:
        return "unknown"
    age = int(match.group(1))
    if age <= 17:
        return "13-17"
    if age <= 24:
        return "18-24"
    if age <= 34:
        return "25-34"
    if age <= 44:
        return "35-44"
    if age <= 54:
        return "45-54"
    return "55+"


def advanced_demographics(events: list[SocialEvent]) -> dict[str, Any]:
    by_user: dict[str, dict[str, str]] = {}
    for event in events:
        if not event.author_pseudo_id:
            continue
        profile = event.public_profile or {}
        row = by_user.setdefault(event.author_pseudo_id, {})
        current_language = str(profile.get("language") or event.language or "unknown").lower()[:20]
        if row.get("language", "unknown") == "unknown" or current_language != "unknown":
            row["language"] = current_language
        geography = _infer_broad_geography(profile)
        if geography != "unknown":
            row["region"] = geography
        interest = _infer_interest(profile)
        if interest != "unknown":
            row["professional_interest"] = interest
        age = _explicit_age_bracket(profile)
        if age != "unknown":
            row["age_bracket"] = age

    total = len(by_user)
    k = SETTINGS.k_anon_min_group

    def aggregate(field: str, method: str) -> dict[str, Any]:
        counts = Counter(row.get(field, "unknown") for row in by_user.values())
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
            "method": method,
        }

    return {
        "unique_anonymized_users": total,
        "language": aggregate("language", "observed-language-signal"),
        "broad_geography": aggregate("region", "public-location-to-broad-region"),
        "professional_interests": aggregate("professional_interest", "public-bio-keyword-interest-v2"),
        "age_brackets": aggregate("age_bracket", "explicit-self-declared-age-only"),
        "privacy_note": (
            "Aggregate anonymized audience signals only. Small groups are suppressed at k="
            f"{k}. Age is never guessed from names/photos/behavior; only explicit self-declared age indicators are used."
        ),
    }


def advanced_trend_metrics(cluster: list[SocialEvent], all_events: list[SocialEvent]) -> dict[str, Any]:
    base = _base_trend_metrics(cluster, all_events)
    if not cluster:
        return {**base, "velocity": 0.0, "momentum": "FLAT", "predicted_next_bucket_volume": 0, "forecast_confidence": 0.0}

    # Derive a transparent near-term projection from observed 15-minute bucket
    # volumes. It is a small prototype forecast, not an internet-wide prediction.
    from .analytics import bucket_time

    counts = Counter(bucket_time(event.created_at) for event in cluster)
    ordered = [counts[key] for key in sorted(counts)]
    if len(ordered) >= 2:
        diffs = [ordered[index] - ordered[index - 1] for index in range(1, len(ordered))]
        recent_diffs = diffs[-3:]
        velocity = sum(recent_diffs) / len(recent_diffs)
        predicted = max(0, round(ordered[-1] + velocity))
        variability = 0.0
        if len(recent_diffs) > 1:
            mean = velocity
            variability = math.sqrt(sum((value - mean) ** 2 for value in recent_diffs) / len(recent_diffs))
        confidence = min(0.9, 0.35 + min(0.35, len(ordered) * 0.07) + max(0.0, 0.2 - variability * 0.05))
    else:
        velocity = float(ordered[-1]) if ordered else 0.0
        predicted = int(ordered[-1]) if ordered else 0
        confidence = 0.25

    if velocity >= 2:
        momentum = "ACCELERATING"
    elif velocity > 0.25:
        momentum = "RISING"
    elif velocity <= -2:
        momentum = "FALLING_FAST"
    elif velocity < -0.25:
        momentum = "DECLINING"
    else:
        momentum = "FLAT"

    return {
        **base,
        "velocity": round(float(velocity), 3),
        "momentum": momentum,
        "predicted_next_bucket_volume": predicted,
        "forecast_confidence": round(float(confidence), 3),
        "forecast_scope": "next observed 15-minute bucket within collected dataset",
    }


def advanced_overview(store) -> dict[str, Any]:
    base = _base_overview(store)
    events = store.list_events(limit=5000)
    emotion_totals: Counter[str] = Counter()
    for event in events:
        for label, value in (event.emotion_scores or {}).items():
            emotion_totals[label] += float(value or 0)
    denom = max(1, len(events))
    emotion_mix = {label: round(value / denom, 4) for label, value in emotion_totals.items()}
    reaction = workspace_reaction_overview(events)
    return {
        **base,
        "emotion_mix": emotion_mix,
        "reaction_overview": reaction,
        "analytics_contract": {
            "emotion_dimensions": list(EMOTION_LEXICONS_V2.keys()),
            "stance_dimensions": ["supportive", "against", "unclear"],
            "sarcasm_separate": True,
            "reaction_post_separation": True,
        },
    }
