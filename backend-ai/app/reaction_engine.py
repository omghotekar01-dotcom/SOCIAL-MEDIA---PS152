from __future__ import annotations

import math
from collections import Counter
from typing import Any

from .schemas import SocialEvent


REACTION_TYPES = {"comment", "reply", "replied_to", "response", "video_comment", "edited_comment"}


def is_reaction(event: SocialEvent) -> bool:
    event_type = (event.event_type or "").lower()
    return bool(event.parent_event_id) or event_type in REACTION_TYPES or "comment" in event_type or "reply" in event_type


def conversation_root(selected: SocialEvent, events: list[SocialEvent]) -> SocialEvent:
    if selected.parent_event_id:
        direct = next(
            (
                event
                for event in events
                if event.platform == selected.platform and event.source_event_id == selected.parent_event_id
            ),
            None,
        )
        if direct:
            return direct

    if selected.conversation_id:
        candidates = [
            event
            for event in events
            if event.platform == selected.platform and event.conversation_id == selected.conversation_id
        ]
        root = next((event for event in candidates if not is_reaction(event)), None)
        if root:
            return root

    return selected


def linked_reactions(root: SocialEvent, events: list[SocialEvent]) -> list[SocialEvent]:
    conversation_id = root.conversation_id or root.source_event_id
    output: list[SocialEvent] = []
    for event in events:
        if event.id == root.id or event.platform != root.platform:
            continue
        if event.parent_event_id and event.parent_event_id == root.source_event_id:
            output.append(event)
            continue
        if conversation_id and event.conversation_id == conversation_id and is_reaction(event):
            output.append(event)
    return sorted(output, key=lambda event: event.created_at)


def _share(counts: Counter[str], key: str, total: int) -> float:
    return round(float(counts.get(key, 0)) / max(1, total), 4)


def summarize_conversation(selected: SocialEvent, events: list[SocialEvent]) -> dict[str, Any]:
    root = conversation_root(selected, events)
    reactions = linked_reactions(root, events)
    n = len(reactions)

    sentiments = Counter((event.sentiment_label or "unknown").lower() for event in reactions)
    stances = Counter((event.stance_label or "unclear").lower() for event in reactions)
    emotion_totals: Counter[str] = Counter()
    sarcasm_total = 0.0
    unique_authors: set[str] = set()
    source_modes = Counter(event.source_mode for event in reactions)

    for event in reactions:
        for label, value in (event.emotion_scores or {}).items():
            emotion_totals[label] += float(value or 0)
        sarcasm_total += float(event.sarcasm_probability or 0)
        if event.author_pseudo_id:
            unique_authors.add(event.author_pseudo_id)

    emotion_means = {
        label: round(total / max(1, n), 4)
        for label, total in sorted(emotion_totals.items())
    }
    negative = _share(sentiments, "negative", n)
    positive = _share(sentiments, "positive", n)
    neutral = _share(sentiments, "neutral", n)
    against = _share(stances, "against", n)
    supportive = _share(stances, "supportive", n)
    sarcasm = round(sarcasm_total / max(1, n), 4)
    anger = float(emotion_means.get("anger", 0))
    anxiety = float(emotion_means.get("anxiety", 0))
    disgust = float(emotion_means.get("disgust", 0))
    polarized = 1.0 if positive >= 0.25 and negative >= 0.25 else 0.0
    volume_signal = min(1.0, n / 30.0)
    diversity = len(unique_authors) / max(1, n)

    # Descriptive attention/reaction risk. This is not a wrongdoing or intent score.
    risk = min(
        1.0,
        0.28 * negative
        + 0.20 * against
        + 0.16 * max(anger, anxiety, disgust)
        + 0.10 * sarcasm
        + 0.10 * volume_signal
        + 0.08 * polarized
        + 0.08 * diversity,
    )
    risk_score = round(risk * 100)
    risk_label = "ESCALATING" if risk_score >= 60 else "WATCH" if risk_score >= 35 else "STABLE"
    confidence = 0.15 if not n else min(0.96, 0.35 + math.log10(n + 1) * 0.34 + min(0.12, diversity * 0.12))

    if not n:
        verdict = "No captured audience replies/comments are linked to this post yet."
    elif negative >= 0.55:
        verdict = "Collected audience reaction is predominantly negative."
    elif positive >= 0.55:
        verdict = "Collected audience reaction is predominantly positive."
    elif polarized:
        verdict = "Collected audience reaction is polarized between positive and negative responses."
    else:
        verdict = "Collected audience reaction is mixed or neutral."

    flags: list[str] = []
    if negative >= 0.55:
        flags.append("negative-reaction-dominant")
    if against >= 0.45:
        flags.append("opposition-elevated")
    if anger >= 0.35:
        flags.append("anger-elevated")
    if anxiety >= 0.35:
        flags.append("anxiety-elevated")
    if disgust >= 0.35:
        flags.append("disgust-elevated")
    if sarcasm >= 0.35:
        flags.append("sarcasm-elevated")
    if polarized:
        flags.append("polarized-opinion")
    if n >= 20:
        flags.append("high-reply-volume")

    return {
        "root_event_id": root.id,
        "root_source_event_id": root.source_event_id,
        "platform": root.platform,
        "reaction_count": n,
        "unique_reaction_authors": len(unique_authors),
        "sentiment_mix": dict(sentiments),
        "stance_mix": dict(stances),
        "emotion_means": emotion_means,
        "negative_share": negative,
        "positive_share": positive,
        "neutral_share": neutral,
        "against_share": against,
        "supportive_share": supportive,
        "sarcasm_mean": sarcasm,
        "risk_score": risk_score,
        "risk_label": risk_label,
        "confidence": round(confidence, 3),
        "verdict": verdict,
        "flags": flags,
        "source_modes": dict(source_modes),
        "sample_reactions": [
            {
                "event_id": event.id,
                "author": event.author_display or event.author_pseudo_id,
                "text": event.text,
                "sentiment": event.sentiment_label,
                "stance": event.stance_label,
                "source_mode": event.source_mode,
                "created_at": event.created_at,
            }
            for event in reactions[:8]
        ],
        "disclosure": "Reaction direction is bounded to captured replies/comments and does not imply wrongdoing, intent, or internet-wide opinion.",
    }


def workspace_reaction_overview(events: list[SocialEvent]) -> dict[str, Any]:
    roots = [event for event in events if not is_reaction(event)]
    summaries = [summarize_conversation(root, events) for root in roots]
    with_reactions = [summary for summary in summaries if summary["reaction_count"] > 0]
    total_reactions = sum(int(summary["reaction_count"]) for summary in with_reactions)

    if not with_reactions:
        return {
            "conversations": len(roots),
            "conversations_with_reactions": 0,
            "captured_reactions": 0,
            "overall_negative_share": 0.0,
            "overall_positive_share": 0.0,
            "overall_against_share": 0.0,
            "overall_supportive_share": 0.0,
            "risk_score": 0,
            "risk_label": "STABLE",
            "escalating_conversations": 0,
            "watch_conversations": 0,
            "coverage": 0.0,
            "note": "No audience replies/comments are captured yet; root-post sentiment is not treated as public opinion.",
        }

    weighted_negative = sum(summary["negative_share"] * summary["reaction_count"] for summary in with_reactions) / max(1, total_reactions)
    weighted_positive = sum(summary["positive_share"] * summary["reaction_count"] for summary in with_reactions) / max(1, total_reactions)
    weighted_against = sum(summary["against_share"] * summary["reaction_count"] for summary in with_reactions) / max(1, total_reactions)
    weighted_support = sum(summary["supportive_share"] * summary["reaction_count"] for summary in with_reactions) / max(1, total_reactions)
    weighted_risk = sum(summary["risk_score"] * summary["reaction_count"] for summary in with_reactions) / max(1, total_reactions)
    risk_score = round(weighted_risk)

    return {
        "conversations": len(roots),
        "conversations_with_reactions": len(with_reactions),
        "captured_reactions": total_reactions,
        "overall_negative_share": round(weighted_negative, 4),
        "overall_positive_share": round(weighted_positive, 4),
        "overall_against_share": round(weighted_against, 4),
        "overall_supportive_share": round(weighted_support, 4),
        "risk_score": risk_score,
        "risk_label": "ESCALATING" if risk_score >= 60 else "WATCH" if risk_score >= 35 else "STABLE",
        "escalating_conversations": sum(1 for summary in with_reactions if summary["risk_label"] == "ESCALATING"),
        "watch_conversations": sum(1 for summary in with_reactions if summary["risk_label"] == "WATCH"),
        "coverage": round(len(with_reactions) / max(1, len(roots)), 4),
        "top_conversations": sorted(with_reactions, key=lambda summary: (summary["risk_score"], summary["reaction_count"]), reverse=True)[:5],
        "note": "Audience reaction aggregates use captured comments/replies only; root-post sentiment remains separate.",
    }
