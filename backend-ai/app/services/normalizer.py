from __future__ import annotations

import hashlib
import re
from typing import Iterable

from ..config import get_settings
from ..schemas import SocialEvent, SocialEventIn

HASHTAG_RE = re.compile(r"#([\w_]+)", re.UNICODE)
MENTION_RE = re.compile(r"@([\w_.-]+)", re.UNICODE)
URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def pseudonymize(platform: str, author_platform_id: str | None) -> str | None:
    if not author_platform_id:
        return None
    settings = get_settings()
    return "usr_" + _hash(f"{settings.pseudonym_salt}:{platform}:{author_platform_id}")[:16]


def normalize_event(event: SocialEventIn) -> SocialEvent:
    text = " ".join((event.text or "").split())
    hashtags = event.hashtags or [m.group(1).lower() for m in HASHTAG_RE.finditer(text)]
    mentions = event.mentions or [m.group(1) for m in MENTION_RE.finditer(text)]
    urls = event.urls or [m.group(0).rstrip(".,)") for m in URL_RE.finditer(text)]

    raw_fingerprint = "|".join(
        [
            event.platform,
            event.source_event_id,
            event.author_platform_id or "",
            event.created_at.isoformat(),
            text,
        ]
    )

    return SocialEvent(
        **event.model_dump(exclude={"hashtags", "mentions", "urls"}),
        hashtags=sorted(set(tag.lower() for tag in hashtags)),
        mentions=sorted(set(mentions)),
        urls=sorted(set(urls)),
        author_pseudo_id=pseudonymize(event.platform, event.author_platform_id),
        raw_hash=_hash(raw_fingerprint),
    )


def normalize_many(events: Iterable[SocialEventIn]) -> list[SocialEvent]:
    return [normalize_event(event) for event in events]
