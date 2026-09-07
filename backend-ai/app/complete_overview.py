from __future__ import annotations

from collections import Counter
from typing import Any

from .advanced_analytics import advanced_overview
from .reaction_engine import is_reaction


def complete_overview(store) -> dict[str, Any]:
    """Workspace overview with explicit content-vs-reaction separation."""
    base = advanced_overview(store)
    events = store.list_events(limit=5000)
    roots = [event for event in events if not is_reaction(event)]
    reactions = [event for event in events if is_reaction(event)]

    root_sentiment = Counter((event.sentiment_label or "unknown") for event in roots)
    reaction_sentiment = Counter((event.sentiment_label or "unknown") for event in reactions)
    reaction_stance = Counter((event.stance_label or "unclear") for event in reactions)

    return {
        **base,
        "root_content_events": len(roots),
        "reaction_events": len(reactions),
        "root_sentiment_mix": dict(root_sentiment),
        "reaction_sentiment_mix": dict(reaction_sentiment),
        "reaction_stance_mix": dict(reaction_stance),
        "sentiment_separation_note": (
            "Root-content sentiment and audience-reaction sentiment are reported separately so the author's message is not mistaken for public opinion."
        ),
    }
