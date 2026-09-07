from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import timezone
from typing import Any

from pydantic import BaseModel, Field
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from .schemas import SocialEvent, SocialEventIn


VADER = SentimentIntensityAnalyzer()
TOKEN_RE = re.compile(r"[#@]?[\w\-'’]+", re.UNICODE)
URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)
MENTION_RE = re.compile(r"@([\w_]+)")
HASHTAG_RE = re.compile(r"#([\w_]+)")
DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
LATIN_RE = re.compile(r"[A-Za-z]")

EMOTION_LEXICONS: dict[str, set[str]] = {
    "joy_excitement": {"happy", "joy", "great", "good", "amazing", "excellent", "excited", "love", "win", "success", "hope", "awesome", "best", "खुश", "खुशी", "अच्छा", "मस्त", "छान", "आनंद", "khush", "accha", "acha", "mast", "chhan", "chan"},
    "anger_frustration": {"angry", "anger", "furious", "outrage", "unacceptable", "hate", "blame", "failed", "failure", "scam", "wrong", "pathetic", "frustrated", "annoyed", "ridiculous", "गुस्सा", "नाराज", "गलत", "बेकार", "राग", "चुकीचे", "वाईट", "gussa", "naraz", "galat", "bekar", "raag"},
    "sadness": {"sad", "sadness", "loss", "lost", "hurt", "sorry", "disappointed", "broken", "regret", "tragic", "cry", "दुख", "दुखी", "निराश", "दुःख", "dukhi", "dukh", "nirash"},
    "fear_anxiety": {"fear", "afraid", "scared", "panic", "unsafe", "uncertain", "worry", "worried", "anxious", "anxiety", "risk", "danger", "threat", "concern", "concerned", "डर", "चिंता", "घबराहट", "धोका", "भीती", "काळजी", "dar", "chinta", "ghabrahat", "dhoka", "bhiti", "kalji"},
    "surprise_shock": {"surprise", "surprised", "shocked", "shock", "unexpected", "unbelievable", "wow", "suddenly", "crazy", "हैरान", "चौंक", "अचानक", "आश्चर्य", "धक्का", "hairan", "achanak", "ashcharya", "dhakka"},
    "trust_confidence": {"trust", "trusted", "reliable", "credible", "confidence", "confident", "believe", "verified", "transparent", "safe", "support", "सही", "भरोसा", "विश्वास", "विश्वसनीय", "bharosa", "vishwas", "sahi"},
    "disgust_aversion": {"disgust", "disgusting", "gross", "shame", "shameful", "nasty", "filthy", "repulsive", "sickening", "boycott", "घिन", "शर्मनाक", "नको", "किळस", "ghin", "sharmanak", "nakko", "kilas"},
    "neutral_informational": set(),
}

SUPPORT_WORDS = {"support", "agree", "agreed", "approve", "approved", "correct", "right", "true", "helpful", "welcome", "trust", "back", "yes", "सही", "समर्थन", "मान्य", "बरोबर", "पाठिंबा", "sahi", "barobar"}
AGAINST_WORDS = {"against", "oppose", "opposed", "wrong", "false", "reject", "rejected", "boycott", "bad", "fail", "failed", "stop", "unacceptable", "गलत", "विरोध", "खोटे", "चुकीचे", "विरोधात", "galat", "virodh", "chukiche"}
TOXIC_WORDS = {"idiot", "stupid", "moron", "hate", "trash", "loser", "shut", "dumb", "fool", "scum", "bloody", "बेवकूफ", "गधा", "चुप", "मूर्ख", "वेडा", "bewakoof", "murkh", "veda"}
SARCASM_PHRASES = {"yeah right", "sure bro", "sure buddy", "totally believable", "what a surprise", "great job", "nice one", "wow genius", "of course", "brilliant decision", "amazing work", "haan bilkul", "wah kya", "क्या बात है"}
POSITIVE_IRONY = {"great", "amazing", "brilliant", "nice", "excellent", "genius", "perfect", "wonderful"}
NEGATIVE_CONTEXT = {"fail", "failed", "wrong", "scam", "unacceptable", "disaster", "pathetic", "ridiculous", "again"}
ROMAN_INDIC = {"bhai", "yaar", "kya", "hai", "nahi", "bahut", "bohot", "accha", "acha", "galat", "sahi", "gussa", "chinta", "mala", "ahe", "khup", "chhan", "barobar", "nakko", "kay", "pan", "aani"}


class TextAnalysisRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    language: str | None = None


class IntelligenceQueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    narrative_id: str | None = None
    limit: int = Field(default=100, ge=1, le=1000)


def _tokens(text: str) -> list[str]:
    return [token.lower().lstrip("#@").strip("_'’-") for token in TOKEN_RE.findall(text.lower()) if token.strip()]


def _softmax(scores: dict[str, float]) -> dict[str, float]:
    maximum = max(scores.values()) if scores else 0.0
    exp = {label: math.exp(score - maximum) for label, score in scores.items()}
    total = sum(exp.values()) or 1.0
    return {label: round(value / total, 4) for label, value in exp.items()}


def detect_code_mix(text: str, language: str | None = None) -> dict[str, Any]:
    devanagari = len(DEVANAGARI_RE.findall(text))
    latin = len(LATIN_RE.findall(text))
    roman_hits = sum(1 for token in _tokens(text) if token in ROMAN_INDIC)
    code_mixed = (devanagari > 0 and latin > 0) or (latin > 0 and roman_hits >= 1)
    return {
        "code_mixed": code_mixed,
        "language_family": "indic-english-code-mixed" if code_mixed else (language or "unknown"),
        "script_counts": {"devanagari": devanagari, "latin": latin},
        "roman_indic_hits": roman_hits,
    }


def _emotion_scores(text: str, compound: float) -> tuple[dict[str, float], list[str]]:
    counts = Counter(_tokens(text))
    raw: dict[str, float] = {}
    evidence: list[str] = []
    for label, lexicon in EMOTION_LEXICONS.items():
        if label == "neutral_informational":
            continue
        matched = [word for word in lexicon if counts[word] > 0]
        hits = sum(counts[word] for word in matched)
        raw[label] = float(hits) * 1.7
        if matched:
            evidence.append(f"{label}: {', '.join(matched[:3])}")

    raw["joy_excitement"] += max(0.0, compound) * 1.15
    raw["trust_confidence"] += max(0.0, compound) * 0.35
    raw["anger_frustration"] += max(0.0, -compound) * 0.72
    raw["sadness"] += max(0.0, -compound) * 0.36
    raw["fear_anxiety"] += max(0.0, -compound) * 0.28
    strength = sum(raw.values())
    raw["neutral_informational"] = max(0.35, 2.1 - strength)
    return _softmax(raw), evidence


def analyze_text(text: str, language: str | None = None) -> dict[str, Any]:
    clean = " ".join((text or "").split())
    lower = clean.lower()
    tokens = set(_tokens(clean))
    compound = float(VADER.polarity_scores(clean)["compound"])
    sentiment = "positive" if compound >= 0.18 else "negative" if compound <= -0.18 else "neutral"

    emotions, emotion_evidence = _emotion_scores(clean, compound)
    primary = max(emotions, key=emotions.get) if emotions else "neutral_informational"

    support_hits = len(tokens & SUPPORT_WORDS)
    against_hits = len(tokens & AGAINST_WORDS)
    if support_hits and against_hits:
        stance, stance_conf = "mixed", min(0.9, 0.58 + 0.06 * (support_hits + against_hits))
    elif support_hits > against_hits:
        stance, stance_conf = "supportive", min(0.97, 0.60 + 0.09 * support_hits)
    elif against_hits > support_hits:
        stance, stance_conf = "against", min(0.97, 0.60 + 0.09 * against_hits)
    else:
        stance, stance_conf = "neutral", 0.50 if abs(compound) < 0.25 else 0.42

    sarcasm = 0.04
    sarcasm_evidence: list[str] = []
    phrase_hits = [phrase for phrase in SARCASM_PHRASES if phrase in lower]
    if phrase_hits:
        sarcasm += min(0.58, 0.24 + 0.13 * len(phrase_hits))
        sarcasm_evidence.append(f"ironic phrase: {phrase_hits[0]}")
    if tokens & POSITIVE_IRONY and (tokens & NEGATIVE_CONTEXT or compound < -0.12):
        sarcasm += 0.30
        sarcasm_evidence.append("positive wording conflicts with negative context")
    if any(mark in clean for mark in ("🙃", "🤡", "😒", "😂")) and compound <= 0.2:
        sarcasm += 0.16
        sarcasm_evidence.append("ironic emoji/context cue")
    sarcasm = round(min(0.96, sarcasm), 3)

    toxic_hits = sorted(tokens & TOXIC_WORDS)
    toxicity = min(0.95, 0.04 + 0.18 * len(toxic_hits) + max(0.0, -compound) * 0.17)
    toxicity_label = "hostile" if toxicity >= 0.62 else "offensive" if toxicity >= 0.28 else "safe"

    length_signal = min(1.0, len(clean) / 120)
    evidence_strength = min(1.0, (len(emotion_evidence) + support_hits + against_hits + len(toxic_hits)) / 5)
    confidence = 0.0 if not clean else min(0.97, 0.46 + 0.24 * length_signal + 0.19 * evidence_strength + 0.08 * abs(compound))
    evidence = emotion_evidence[:4]
    if stance != "neutral":
        evidence.append(f"stance cues: support={support_hits}, against={against_hits}")
    evidence.extend(sarcasm_evidence[:2])
    if toxic_hits:
        evidence.append(f"toxicity cues: {', '.join(toxic_hits[:3])}")
    if not evidence:
        evidence.append("low lexical evidence; sentiment prior and neutral baseline used")

    return {
        "sentiment_label": sentiment,
        "sentiment_score": round(compound, 4),
        "emotion_scores": emotions,
        "primary_emotion": primary,
        "primary_emotion_confidence": round(emotions.get(primary, 0.0), 4),
        "stance_label": stance,
        "stance_confidence": round(stance_conf, 3),
        "sarcasm_probability": sarcasm,
        "toxicity_probability": round(toxicity, 3),
        "toxicity_label": toxicity_label,
        "code_mix": detect_code_mix(clean, language),
        "confidence": round(confidence, 3),
        "evidence": evidence,
        "inference_method": "nexus-multidimensional-offline-v2",
        "model_note": "Offline deterministic fallback with stable API contract; a production transformer can replace the adapter.",
    }


def _topic_terms(text: str, top_k: int = 6) -> list[str]:
    stop = {"the", "and", "for", "this", "that", "with", "from", "have", "has", "are", "was", "were", "will", "would", "about", "into", "just", "your", "our", "their", "you", "they", "but", "not", "very", "hai", "nahi", "ahe"}
    words = [token for token in _tokens(text) if len(token) >= 3 and token not in stop]
    return [word for word, _ in Counter(words).most_common(top_k)]


def enrich_event_v2(event: SocialEventIn) -> tuple[SocialEventIn, dict[str, Any]]:
    normalized = event.model_copy(update={
        "mentions": sorted(set(event.mentions) | set(MENTION_RE.findall(event.text))),
        "hashtags": sorted(set(event.hashtags) | {tag.lower() for tag in HASHTAG_RE.findall(event.text)}),
        "urls": sorted(set(event.urls) | set(URL_RE.findall(event.text))),
    })
    result = analyze_text(normalized.text, normalized.language)
    return normalized, {
        "sentiment_label": result["sentiment_label"],
        "sentiment_score": result["sentiment_score"],
        "emotion_scores": result["emotion_scores"],
        "stance_label": result["stance_label"],
        "stance_confidence": result["stance_confidence"],
        "sarcasm_probability": result["sarcasm_probability"],
        "topic_terms": _topic_terms(normalized.text),
        "quality_score": result["confidence"],
        "inference_method": result["inference_method"],
    }


def intelligence_summary(events: list[SocialEvent]) -> dict[str, Any]:
    if not events:
        return {"total_events": 0, "emotion_mix": {}, "stance_mix": {}, "toxicity_mix": {}, "sarcasm": {"average": 0.0, "high_probability_events": 0}, "languages": {}, "code_mixed_events": 0, "platforms": {}, "emotion_timeline": [], "confidence": 0.0}

    emotion_totals: defaultdict[str, float] = defaultdict(float)
    stance, toxicity, platforms, languages = Counter(), Counter(), Counter(), Counter()
    sarcasm_values: list[float] = []
    confidence_values: list[float] = []
    code_mixed = 0
    timeline: defaultdict[str, Counter] = defaultdict(Counter)

    for event in events:
        result = analyze_text(event.text, event.language)
        for label, score in result["emotion_scores"].items():
            emotion_totals[label] += float(score)
        stance[result["stance_label"]] += 1
        toxicity[result["toxicity_label"]] += 1
        platforms[event.platform] += 1
        languages[event.language or "unknown"] += 1
        code_mixed += int(result["code_mix"]["code_mixed"])
        sarcasm_values.append(float(result["sarcasm_probability"]))
        confidence_values.append(float(result["confidence"]))
        utc = event.created_at.astimezone(timezone.utc)
        bucket = utc.replace(minute=(utc.minute // 15) * 15, second=0, microsecond=0).isoformat()
        timeline[bucket][result["primary_emotion"]] += 1

    n = len(events)
    emotion_mix = {label: round(value / n, 4) for label, value in sorted(emotion_totals.items(), key=lambda item: item[1], reverse=True)}
    return {
        "total_events": n,
        "primary_emotion": max(emotion_mix, key=emotion_mix.get) if emotion_mix else "neutral_informational",
        "emotion_mix": emotion_mix,
        "stance_mix": dict(stance),
        "toxicity_mix": dict(toxicity),
        "sarcasm": {"average": round(sum(sarcasm_values) / n, 3), "high_probability_events": sum(1 for value in sarcasm_values if value >= 0.60)},
        "languages": dict(languages),
        "code_mixed_events": code_mixed,
        "platforms": dict(platforms),
        "emotion_timeline": [{"time": time, "emotions": dict(counts), "total": sum(counts.values())} for time, counts in sorted(timeline.items())],
        "confidence": round(sum(confidence_values) / n, 3),
        "method": "event-level recomputation using nexus-multidimensional-offline-v2",
    }


def narrative_intelligence(events: list[SocialEvent]) -> dict[str, Any]:
    ordered = sorted(events, key=lambda event: event.created_at)
    summary = intelligence_summary(ordered)
    if not ordered:
        return {**summary, "propagation": [], "cross_platform_latency_minutes": None, "emotion_shift": None}

    first_by_platform: dict[str, Any] = {}
    seen: set[str] = set()
    propagation: list[dict[str, Any]] = []
    for event in ordered:
        result = analyze_text(event.text, event.language)
        first_by_platform.setdefault(event.platform, event.created_at)
        is_entry = event.platform not in seen
        seen.add(event.platform)
        propagation.append({"event_id": event.id, "created_at": event.created_at, "platform": event.platform, "author_pseudo_id": event.author_pseudo_id, "primary_emotion": result["primary_emotion"], "stance": result["stance_label"], "sarcasm_probability": result["sarcasm_probability"], "is_platform_entry": is_entry, "text": event.text[:240]})

    platform_times = sorted(first_by_platform.items(), key=lambda item: item[1])
    latency = round((platform_times[1][1] - platform_times[0][1]).total_seconds() / 60, 2) if len(platform_times) >= 2 else None
    split = max(1, len(ordered) // 2)
    early = intelligence_summary(ordered[:split])
    late = intelligence_summary(ordered[split:]) if ordered[split:] else early
    labels = set(early.get("emotion_mix", {})) | set(late.get("emotion_mix", {}))
    deltas = {label: round(late.get("emotion_mix", {}).get(label, 0.0) - early.get("emotion_mix", {}).get(label, 0.0), 4) for label in labels}
    biggest = max(deltas, key=lambda key: abs(deltas[key])) if deltas else None

    return {
        **summary,
        "first_observed_at": ordered[0].created_at,
        "last_observed_at": ordered[-1].created_at,
        "origin_event_id": ordered[0].id,
        "origin_scope_note": "Earliest event in the collected dataset, not a claim of absolute internet origin.",
        "cross_platform_latency_minutes": latency,
        "platform_entry_order": [{"platform": platform, "first_seen": observed} for platform, observed in platform_times],
        "emotion_shift": {"largest_change": biggest, "deltas": deltas},
        "propagation": propagation,
    }


def answer_intelligence_query(events: list[SocialEvent], request: IntelligenceQueryRequest) -> dict[str, Any]:
    selected = [event for event in events if request.narrative_id is None or event.narrative_cluster_id == request.narrative_id][-request.limit:]
    summary = intelligence_summary(selected)
    q = request.question.lower()
    if any(word in q for word in ("emotion", "anger", "fear", "anxiety")):
        answer = f"Dominant emotion is {summary.get('primary_emotion', 'unknown')} across {len(selected)} matching events."
        evidence = sorted(summary.get("emotion_mix", {}).items(), key=lambda item: item[1], reverse=True)[:4]
    elif any(word in q for word in ("stance", "support", "against")):
        mix = summary.get("stance_mix", {})
        dominant = max(mix, key=mix.get) if mix else "unknown"
        answer = f"Dominant stance is {dominant} across {len(selected)} matching events."
        evidence = sorted(mix.items(), key=lambda item: item[1], reverse=True)
    elif "sarcasm" in q:
        sarcasm = summary.get("sarcasm", {})
        answer = f"Average sarcasm probability is {sarcasm.get('average', 0):.0%}; {sarcasm.get('high_probability_events', 0)} events are above 0.60."
        evidence = [("average", sarcasm.get("average", 0)), ("high_probability_events", sarcasm.get("high_probability_events", 0))]
    else:
        answer = f"Analyzed {len(selected)} collected events. Dominant emotion: {summary.get('primary_emotion', 'unknown')}; confidence: {summary.get('confidence', 0):.0%}."
        evidence = sorted(summary.get("emotion_mix", {}).items(), key=lambda item: item[1], reverse=True)[:4]
    return {"question": request.question, "answer": answer, "evidence": evidence, "scope": "Only the configured/collected public or authorized dataset is analyzed.", "event_count": len(selected)}
