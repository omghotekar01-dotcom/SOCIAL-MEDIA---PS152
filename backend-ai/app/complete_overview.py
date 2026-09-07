from __future__ import annotations

from collections import Counter
from typing import Any

from .advanced_analytics import EMOTION_LEXICONS_V2, advanced_overview
from .reaction_engine import is_reaction, workspace_reaction_overview


def complete_overview(store) -> dict[str, Any]:
    """Workspace overview with untruncated content-vs-reaction analytics."""
    base = advanced_overview(store)
    events = store.list_events(limit=None)
    roots = [event for event in events if not is_reaction(event)]
    reactions = [event for event in events if is_reaction(event)]

    root_sentiment = Counter((event.sentiment_label or "unknown") for event in roots)
    reaction_sentiment = Counter((event.sentiment_label or "unknown") for event in reactions)
    reaction_stance = Counter((event.stance_label or "unclear") for event in reactions)

    emotion_totals: Counter[str] = Counter()
    for event in events:
        for label, value in (event.emotion_scores or {}).items():
            emotion_totals[label] += float(value or 0)
    denom = max(1, len(events))
    emotion_mix = {
        label: round(float(emotion_totals.get(label, 0.0)) / denom, 4)
        for label in EMOTION_LEXICONS_V2
    }

    return {
        **base,
        "total_events": len(events),
        "root_content_events": len(roots),
        "reaction_events": len(reactions),
        "root_sentiment_mix": dict(root_sentiment),
        "reaction_sentiment_mix": dict(reaction_sentiment),
        "reaction_stance_mix": dict(reaction_stance),
        "emotion_mix": emotion_mix,
        "reaction_overview": workspace_reaction_overview(events),
        "analytics_population": "all events in the active workspace; no 500/5000 reaction sampling cap",
        "sentiment_separation_note": (
            "Root-content sentiment and audience-reaction sentiment are reported separately so the author's message is not mistaken for public opinion."
        ),
    }
