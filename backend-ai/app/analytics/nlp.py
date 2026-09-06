from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from functools import lru_cache
from typing import Any

from langdetect import detect as lang_detect
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from ..config import get_settings

TOKEN_RE = re.compile(r"[\w#@']+", re.UNICODE)
STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "to", "of", "and", "or", "for",
    "in", "on", "at", "it", "this", "that", "with", "from", "be", "as", "by", "we",
    "you", "they", "he", "she", "i", "our", "your", "their", "has", "have", "had",
}
ANXIETY = {"worried", "worry", "panic", "fear", "afraid", "uncertain", "rumour", "rumor", "warning", "urgent", "danger", "closed"}
ANGER = {"angry", "outrage", "unacceptable", "blame", "fraud", "lie", "lying", "hate", "shame"}
EXCITEMENT = {"wow", "great", "amazing", "excited", "finally", "breaking", "huge", "excellent"}
SUPPORT = {"support", "agree", "yes", "correct", "confirmed", "true", "right"}
AGAINST = {"against", "disagree", "no", "false", "fake", "wrong", "not", "deny", "denied"}
UNCERTAIN = {"maybe", "may", "possibly", "unconfirmed", "uncertain", "reportedly", "rumour", "rumor", "claim"}

_vader = SentimentIntensityAnalyzer()


def tokens(text: str) -> list[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text or "")]


def detect_language(text: str) -> str:
    if not (text or "").strip():
        return "unknown"
    try:
        return lang_detect(text)
    except Exception:
        devanagari = sum("\u0900" <= ch <= "\u097f" for ch in text)
        return "hi" if devanagari >= 2 else "en"


def _distribution(scores: dict[str, float]) -> tuple[str, float]:
    if not scores:
        return "neutral", 0.5
    label, value = max(scores.items(), key=lambda kv: kv[1])
    total = sum(max(v, 0.0) for v in scores.values()) or 1.0
    confidence = 0.5 + 0.47 * (max(value, 0.0) / total)
    return label, round(min(confidence, 0.97), 3)


def _fallback_analysis(text: str) -> dict[str, Any]:
    toks = tokens(text)
    counts = Counter(toks)
    vader = _vader.polarity_scores(text or "")
    compound = float(vader.get("compound", 0.0))
    if compound >= 0.2:
        sentiment_label = "positive"
    elif compound <= -0.2:
        sentiment_label = "negative"
    else:
        sentiment_label = "neutral"
    sentiment_confidence = round(min(0.96, 0.55 + abs(compound) * 0.4), 3)

    emotion_scores = {
        "anxiety": float(sum(counts[t] for t in ANXIETY)),
        "anger": float(sum(counts[t] for t in ANGER)),
        "excitement": float(sum(counts[t] for t in EXCITEMENT)),
        "neutral": 0.45,
    }
    emotion_label, emotion_confidence = _distribution(emotion_scores)
    emotion_total = sum(emotion_scores.values()) or 1.0
    emotion_probabilities = {k: round(v / emotion_total, 3) for k, v in emotion_scores.items()}

    stance_scores = {
        "supportive": float(sum(counts[t] for t in SUPPORT)),
        "against": float(sum(counts[t] for t in AGAINST)),
        "uncertain": float(sum(counts[t] for t in UNCERTAIN)) + 0.3,
    }
    stance_label, stance_confidence = _distribution(stance_scores)

    lower = (text or "").lower()
    sarcasm_markers = sum(marker in lower for marker in ("yeah right", "sure...", "obviously", "totally", "/s"))
    sarcasm_probability = min(0.92, 0.08 + 0.24 * sarcasm_markers + (0.08 if "?!" in text or "!?" in text else 0.0))

    keywords: list[str] = []
    for token, _ in counts.most_common():
        clean = token.lstrip("#@")
        if len(clean) < 3 or clean in STOPWORDS:
            continue
        keywords.append(clean)
        if len(keywords) >= 10:
            break

    return {
        "language": detect_language(text),
        "sentiment_label": sentiment_label,
        "sentiment_score": round(compound, 3),
        "sentiment_confidence": sentiment_confidence,
        "emotion_label": emotion_label,
        "emotion_confidence": emotion_confidence,
        "emotion_scores": emotion_probabilities,
        "stance_label": stance_label,
        "stance_confidence": stance_confidence,
        "sarcasm_probability": round(sarcasm_probability, 3),
        "topic_terms": keywords,
        "inference_method": "vader+lexical-local",
    }


@lru_cache(maxsize=1)
def _transformer_pipeline():
    settings = get_settings()
    if not settings.nexus_enable_transformers:
        return None
    try:
        from transformers import pipeline
        return pipeline("sentiment-analysis", model=settings.nexus_sentiment_model)
    except Exception:
        return None


def analyze_text(text: str) -> dict[str, Any]:
    result = _fallback_analysis(text)
    pipe = _transformer_pipeline()
    if not pipe:
        return result
    try:
        output = pipe(text[:2000], truncation=True)[0]
        label = str(output.get("label", "")).lower()
        score = float(output.get("score", 0.0))
        if "negative" in label or label.endswith("0"):
            normalized = "negative"
        elif "positive" in label or label.endswith("2"):
            normalized = "positive"
        else:
            normalized = "neutral"
        result["sentiment_label"] = normalized
        result["sentiment_score"] = round((1 if normalized == "positive" else -1 if normalized == "negative" else 0) * score, 3)
        result["sentiment_confidence"] = round(score, 3)
        result["inference_method"] = f"transformer:{get_settings().nexus_sentiment_model}+lexical"
    except Exception:
        pass
    return result


def fingerprint(text: str, dimensions: int = 384) -> list[float]:
    """Zero-download local fingerprint based on hashed unigrams/bigrams.

    It gives deterministic semantic-ish similarity for the demo. The interface is
    intentionally vector-compatible so sentence-transformer embeddings can replace
    it later without touching clustering/lineage code.
    """
    toks = [t for t in tokens(text) if t not in STOPWORDS]
    features = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
    vector = [0.0] * dimensions
    for feature in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        idx = int.from_bytes(digest, "big") % dimensions
        vector[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return float(sum(x * y for x, y in zip(a, b)))
