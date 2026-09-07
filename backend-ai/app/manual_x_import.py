from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

from .free_connectors import _extract_text_entities
from .schemas import SocialEventIn, XManualConversationRequest


def _canonical_x_url(value: str) -> str:
    parsed = urlparse(value.strip())
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host.startswith("mobile."):
        host = host[7:]
    if host == "twitter.com":
        host = "x.com"
    return urlunparse(("https", host, parsed.path.rstrip("/"), "", "", ""))


def _status_id(url: str) -> str:
    match = re.search(r"/status/(\d+)", url)
    return match.group(1) if match else uuid4().hex[:18]


def _username(url: str, explicit: str | None) -> str:
    if explicit and explicit.strip():
        return explicit.strip().lstrip("@")
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    return parts[0] if parts else "X author"


def build_manual_x_events(request: XManualConversationRequest) -> list[SocialEventIn]:
    """Convert analyst-transcribed public X evidence into linked IMPORT events.

    This exists specifically for provider-limited prototype/demo situations. It
    never claims the content was fetched through X APIs. The original permalink,
    import method and timestamp provenance stay attached to every event.
    """

    canonical = _canonical_x_url(request.url)
    status_id = _status_id(canonical)
    author = _username(canonical, request.author)
    root_time = request.created_at or datetime.now(timezone.utc)
    run_id = f"x-manual-{uuid4().hex[:10]}"
    root_source_id = f"manual:{status_id}"

    hashtags, mentions, urls = _extract_text_entities(request.post_text)
    common_profile = {
        "username": author,
        "original_x_url": canonical,
        "collection_scope": "analyst_manual_public_x",
        "evidence_entry_method": "manual_transcription",
        "provider_access_note": "X API/oEmbed did not expose this conversation; analyst pasted public evidence.",
    }

    root = SocialEventIn(
        platform="x",
        source_event_id=root_source_id,
        event_type="manual_public_post",
        author_platform_id=author,
        author_display=author,
        text=request.post_text,
        created_at=root_time,
        url=canonical,
        conversation_id=status_id,
        mentions=mentions,
        hashtags=hashtags,
        urls=urls,
        engagement={},
        public_profile={
            **common_profile,
            "timestamp_source": "analyst_provided" if request.created_at else "import_time_fallback",
            "manual_reply_count": len(request.replies),
        },
        source_mode="IMPORT",
        connector_run_id=run_id,
    )

    output = [root]
    for index, reply in enumerate(request.replies, start=1):
        text = reply.text.strip()
        if not text:
            continue
        r_hashtags, r_mentions, r_urls = _extract_text_entities(text)
        reply_author = (reply.author or f"reply-{index}").strip().lstrip("@") or f"reply-{index}"
        reply_time = reply.created_at or (root_time + timedelta(seconds=index))
        output.append(
            SocialEventIn(
                platform="x",
                source_event_id=f"manual-reply:{status_id}:{index}",
                event_type="reply",
                author_platform_id=reply_author,
                author_display=reply_author,
                text=text,
                created_at=reply_time,
                parent_event_id=root_source_id,
                conversation_id=status_id,
                mentions=r_mentions,
                hashtags=r_hashtags,
                urls=r_urls,
                engagement={"likes": reply.likes},
                public_profile={
                    **common_profile,
                    "manual_reply_index": index,
                    "timestamp_source": "analyst_provided" if reply.created_at else "import_time_fallback",
                },
                source_mode="IMPORT",
                connector_run_id=run_id,
            )
        )
    return output
