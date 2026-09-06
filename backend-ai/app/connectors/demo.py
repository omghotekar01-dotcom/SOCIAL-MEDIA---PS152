from __future__ import annotations

import json
from pathlib import Path

from ..config import ROOT_DIR
from ..schemas import SocialEvent, SocialEventIn
from ..services.normalizer import normalize_many

DEMO_PATH = ROOT_DIR / "data" / "demo" / "metro_rain_events.json"


def load_demo_events(path: Path | None = None) -> list[SocialEvent]:
    source = path or DEMO_PATH
    payload = json.loads(source.read_text(encoding="utf-8"))
    events = [SocialEventIn.model_validate(item) for item in payload]
    return normalize_many(events)
