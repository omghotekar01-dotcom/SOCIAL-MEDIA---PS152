from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from .advanced_analytics import EMOTION_LEXICONS_V2
from .reaction_engine import is_reaction
from .stable_views import stable_timeline


def _bucket_time(dt: datetime, minutes: int) -> datetime:
    dt = dt.astimezone(timezone.utc)
    minute = (dt.minute // minutes) * minutes
    return dt.replace(minute=minute, second=0, microsecond=0)


def ps26152_timeline(events: list[Any], minutes: int = 15) -> list[dict[str, Any]]:
    """Chronology with volume, polarity, nuanced emotions, stance and sarcasm.

    The base timeline preserves sparse/zero visual padding. Enrichment is only
    calculated for buckets that contain real evidence; visual padding remains
    explicitly zero-volume and never becomes synthetic sentiment evidence.
    """
    base = stable_timeline(events, minutes)
    groups: dict[datetime, list[Any]] = defaultdict(list)
    for event in events:
        groups[_bucket_time(event.created_at, minutes)].append(event)

    output: list[dict[str, Any]] = []
    for row in base:
        time = row["time"]
        group = groups.get(time, [])
        reactions = [event for event in group if is_reaction(event)]
        stance = Counter((event.stance_label or "unclear") for event in reactions)
        emotions: dict[str, float] = {}
        for label in EMOTION_LEXICONS_V2:
            emotions[label] = round(
                sum(float((event.emotion_scores or {}).get(label, 0.0) or 0.0) for event in group) / max(1, len(group)),
                4,
            ) if group else 0.0
        output.append(
            {
                **row,
                "reaction_count": len(reactions),
                "root_count": len(group) - len(reactions),
                "stance": dict(stance),
                "supportive_share": round(stance.get("supportive", 0) / max(1, len(reactions)), 4) if reactions else 0.0,
                "against_share": round(stance.get("against", 0) / max(1, len(reactions)), 4) if reactions else 0.0,
                "sarcasm_mean": round(sum(float(event.sarcasm_probability or 0.0) for event in group) / max(1, len(group)), 4) if group else 0.0,
                "emotions": emotions,
            }
        )
    return output
