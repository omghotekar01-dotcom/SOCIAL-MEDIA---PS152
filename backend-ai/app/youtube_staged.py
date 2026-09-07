from __future__ import annotations

import asyncio
import json
import re
from typing import Any
from uuid import uuid4

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
_BACKGROUND_GENERATIONS: dict[str, str] = {}
_BACKGROUND_TASK_GENERATIONS: dict[str, str] = {}


def _video_id(value: str) -> str | None:
    clean = (value or "").strip()
    if _YOUTUBE_ID_RE.fullmatch(clean):
        return clean
    for pattern in _YOUTUBE_URL_RES:
        match = pattern.search(clean)
        if match:
            return match.group(1)
    return None


def _root(video_id: str):
    store = get_store()
    return next(
        (
            event
            for event in store.list_events(limit=None, platform="youtube")
            if event.source_event_id == f"video:{video_id}"
        ),
        None,
    )


def _root_matches(video_id: str, generation: str) -> bool:
    root = _root(video_id)
    if not root:
        return False
    profile = dict(root.public_profile or {})
    return str(profile.get("background_collection_token") or "") == generation


async def _wait_for_root(video_id: str, generation: str, timeout_seconds: float = 6.0) -> bool:
    """Wait for the FastAPI route to persist the fast-first root before crawling.

    The connector starts the background task before its initial result is ingested
    by the route. Waiting on the generation token removes a race where a very short
    conversation could finish its background request before the root existed.
    """
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        if _root_matches(video_id, generation):
            return True
        await asyncio.sleep(0.05)
    return False


def _update_root_profile(video_id: str, values: dict[str, Any], *, generation: str | None = None) -> None:
    store = get_store()
    root = _root(video_id)
    if not root:
        return
    profile = dict(root.public_profile or {})
    if generation is not None and str(profile.get("background_collection_token") or "") != generation:
        return
    profile.update(values)
    with store.connect() as conn:
        conn.execute(
            "UPDATE events SET public_profile = ? WHERE platform = 'youtube' AND source_event_id = ?",
            (json.dumps(profile, ensure_ascii=False), f"video:{video_id}"),
        )


def _ingest_background(events: list[SocialEventIn], *, video_id: str, query: str, generation: str) -> None:
    """Insert exhaustive results only into the exact foreground search generation.

    Matching on video id alone is insufficient: an analyst can reset the workspace
    and load the same video again while an older crawl is still in flight. The
    generation token prevents that stale task from contaminating the new analysis.
    """
    if not events or not _root_matches(video_id, generation):
        return

    store = get_store()
    inserted = 0
    for incoming in events:
        # Re-check before every insert so a reset in the middle of a large batch
        # stops the stale job immediately rather than after it has polluted data.
        if not _root_matches(video_id, generation):
            return
        profile = dict(incoming.public_profile or {})
        profile.update(
            {
                "connector": "youtube_data_api_v3_exhaustive_background",
                "search_query": query,
                "collection_mode": "background_exhaustive",
                "background_collection_token": generation,
            }
        )
        stamped = incoming.model_copy(update={"public_profile": profile})
        normalized, derived = analytics.enrich_event(stamped)
        if store.insert(normalized, derived) is not None:
            inserted += 1

    if not _root_matches(video_id, generation):
        return

    full_root = events[0]
    full_profile: dict[str, Any] = dict(full_root.public_profile or {})
    full_profile.update(
        {
            "connector": "youtube_data_api_v3_exhaustive_background",
            "search_query": query,
            "collection_mode": "background_exhaustive",
            "background_collection_state": "complete",
            "background_collection_token": generation,
            "background_inserted_events": inserted,
        }
    )
    with store.connect() as conn:
        conn.execute(
            "UPDATE events SET public_profile = ? WHERE platform = 'youtube' AND source_event_id = ?",
            (json.dumps(full_profile, ensure_ascii=False), f"video:{video_id}"),
        )

    if inserted:
        analytics.assign_clusters(store)


async def _background_exhaustive(query: str, video_id: str, generation: str) -> None:
    try:
        if not await _wait_for_root(video_id, generation):
            return
        events = await _exhaustive_youtube_search(
            YouTubeSearchRequest(query=query, max_videos=1, max_comments_per_video=0)
        )
        await asyncio.to_thread(
            _ingest_background,
            events,
            video_id=video_id,
            query=query,
            generation=generation,
        )
    except asyncio.CancelledError:
        _update_root_profile(
            video_id,
            {
                "background_collection_state": "cancelled",
                "background_collection_note": "Background crawl was cancelled because a newer workspace/search superseded it.",
            },
            generation=generation,
        )
        raise
    except Exception as exc:
        _update_root_profile(
            video_id,
            {
                "background_collection_state": "error",
                "background_collection_note": str(exc)[:300],
            },
            generation=generation,
        )
    finally:
        if _BACKGROUND_TASK_GENERATIONS.get(video_id) == generation:
            _BACKGROUND_TASKS.pop(video_id, None)
            _BACKGROUND_TASK_GENERATIONS.pop(video_id, None)


def cancel_youtube_background_tasks() -> int:
    """Cancel in-flight exhaustive jobs before a workspace reset/new search."""
    cancelled = 0
    for task in list(_BACKGROUND_TASKS.values()):
        if not task.done():
            task.cancel()
            cancelled += 1
    _BACKGROUND_TASKS.clear()
    _BACKGROUND_TASK_GENERATIONS.clear()
    _BACKGROUND_GENERATIONS.clear()
    return cancelled


def _start_background(query: str, video_id: str) -> None:
    generation = _BACKGROUND_GENERATIONS.get(video_id)
    if not generation:
        return

    existing = _BACKGROUND_TASKS.get(video_id)
    existing_generation = _BACKGROUND_TASK_GENERATIONS.get(video_id)
    if existing and not existing.done():
        if existing_generation == generation:
            return
        existing.cancel()

    task = asyncio.create_task(
        _background_exhaustive(query, video_id, generation),
        name=f"youtube-exhaustive-{video_id}-{generation[:6]}",
    )
    _BACKGROUND_TASKS[video_id] = task
    _BACKGROUND_TASK_GENERATIONS[video_id] = generation


async def youtube_staged_search(request: YouTubeSearchRequest) -> list[SocialEventIn]:
    """Fast-first exact-video collection with exhaustive background completion.

    Exact YouTube URLs/video IDs return a first analytical sample quickly and
    continue provider-bounded exhaustive collection in a server-side task. The
    root event exposes ``background_collection_state`` so the frontend can refresh
    only when the crawl completes, without running heavy overview analytics on a
    polling loop.
    """
    video_id = _video_id(request.query)
    if not video_id or request.max_comments_per_video > 0:
        return await _exhaustive_youtube_search(request)

    initial_request = request.model_copy(
        update={"max_videos": 1, "max_comments_per_video": _FAST_FIRST_REACTIONS}
    )
    initial = await _exhaustive_youtube_search(initial_request)

    if initial:
        generation = uuid4().hex
        _BACKGROUND_GENERATIONS[video_id] = generation
        root_profile = dict(initial[0].public_profile or {})
        root_profile.update(
            {
                "collection_mode": "fast_first_background_full",
                "background_collection_state": "running",
                "background_collection_token": generation,
                "fast_first_reaction_target": _FAST_FIRST_REACTIONS,
            }
        )
        initial[0] = initial[0].model_copy(update={"public_profile": root_profile})
        _start_background(request.query, video_id)

    return initial
