from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from . import analytics
from .db import get_store
from .schemas import SocialEventIn, YouTubeSearchRequest
from .youtube_official import youtube_official_search as _exhaustive_youtube_search


_YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YOUTUBE_URL_RES = [
    re.compile(r"(?:youtube\.com/watch\?(?:[^#\s]*&)?v=)([A-Za-z0-9_-]{11})", re.I),
    re.compile(r"(?:youtu\.be/)([A-Za-z0-9_-]{11})", re.I),
    re.compile(r"(?:youtube\.com/(?:shorts|live|embed)/)([A-Za-z0-9_-]{11})", re.I),
]

_FAST_FIRST_REACTIONS = 50
_BACKGROUND_TASKS: dict[str, asyncio.Task] = {}


def _video_id(value: str) -> str | None:
    clean = (value or "").strip()
    if _YOUTUBE_ID_RE.fullmatch(clean):
        return clean
    for pattern in _YOUTUBE_URL_RES:
        match = pattern.search(clean)
        if match:
            return match.group(1)
    return None


def _root_exists(video_id: str) -> bool:
    store = get_store()
    source_id = f"video:{video_id}"
    return any(
        event.platform == "youtube" and event.source_event_id == source_id
        for event in store.list_events(limit=None)
    )


def _ingest_background(events: list[SocialEventIn], *, video_id: str, query: str) -> None:
    """Insert the exhaustive result only if its foreground root is still active.

    This prevents a slow crawl for an old URL from contaminating a workspace that
    the analyst has already reset for another search.
    """
    if not events or not _root_exists(video_id):
        return

    store = get_store()
    inserted = 0
    for incoming in events:
        profile = dict(incoming.public_profile or {})
        profile.update(
            {
                "connector": "youtube_data_api_v3_exhaustive_background",
                "search_query": query,
                "collection_mode": "background_exhaustive",
            }
        )
        stamped = incoming.model_copy(update={"public_profile": profile})
        normalized, derived = analytics.enrich_event(stamped)
        if store.insert(normalized, derived) is not None:
            inserted += 1

    # The exhaustive root duplicates the fast root and is therefore not inserted.
    # Update its public metadata in-place so the UI reports the final coverage,
    # captured count, page count and stop reason rather than the first 50 sample.
    full_root = events[0]
    full_profile: dict[str, Any] = dict(full_root.public_profile or {})
    full_profile.update(
        {
            "connector": "youtube_data_api_v3_exhaustive_background",
            "search_query": query,
            "collection_mode": "background_exhaustive",
        }
    )
    with store.connect() as conn:
        conn.execute(
            "UPDATE events SET public_profile = ? WHERE platform = 'youtube' AND source_event_id = ?",
            (json.dumps(full_profile, ensure_ascii=False), f"video:{video_id}"),
        )

    if inserted:
        analytics.assign_clusters(store)


async def _background_exhaustive(query: str, video_id: str) -> None:
    try:
        events = await _exhaustive_youtube_search(
            YouTubeSearchRequest(query=query, max_videos=1, max_comments_per_video=0)
        )
        await asyncio.to_thread(_ingest_background, events, video_id=video_id, query=query)
    finally:
        _BACKGROUND_TASKS.pop(video_id, None)


def _start_background(query: str, video_id: str) -> None:
    existing = _BACKGROUND_TASKS.get(video_id)
    if existing and not existing.done():
        return
    task = asyncio.create_task(
        _background_exhaustive(query, video_id),
        name=f"youtube-exhaustive-{video_id}",
    )
    _BACKGROUND_TASKS[video_id] = task


async def youtube_staged_search(request: YouTubeSearchRequest) -> list[SocialEventIn]:
    """Fast-first exact-video collection with exhaustive background completion.

    Exact YouTube URLs/video IDs no longer keep the browser waiting for the whole
    public conversation. NEXUS returns a first analytical sample quickly, then
    continues provider-bounded exhaustive collection in a server-side task.

    Keyword searches preserve the normal connector behavior because they may
    select several videos and are better controlled through the ordinary source
    workflow / Live Watch.
    """
    video_id = _video_id(request.query)
    if not video_id or request.max_comments_per_video > 0:
        return await _exhaustive_youtube_search(request)

    initial_request = request.model_copy(
        update={"max_videos": 1, "max_comments_per_video": _FAST_FIRST_REACTIONS}
    )
    initial = await _exhaustive_youtube_search(initial_request)

    if initial:
        root_profile = dict(initial[0].public_profile or {})
        root_profile.update(
            {
                "collection_mode": "fast_first_background_full",
                "background_collection_state": "running",
                "fast_first_reaction_target": _FAST_FIRST_REACTIONS,
            }
        )
        initial[0] = initial[0].model_copy(update={"public_profile": root_profile})
        _start_background(request.query, video_id)

    return initial
