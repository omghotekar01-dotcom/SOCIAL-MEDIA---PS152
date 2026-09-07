from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app import youtube_staged
from app.schemas import SocialEventIn, YouTubeSearchRequest


def _root(video_id: str) -> SocialEventIn:
    return SocialEventIn(
        platform="youtube",
        source_event_id=f"video:{video_id}",
        event_type="video",
        author_display="Demo Channel",
        text="Demo video",
        created_at=datetime.now(timezone.utc),
        url=f"https://www.youtube.com/watch?v={video_id}",
        conversation_id=video_id,
        public_profile={"captured_comment_count": 3, "comments_state": "available"},
        source_mode="LIVE",
    )


def test_exact_video_returns_fast_sample_and_starts_background(monkeypatch):
    calls: list[int] = []
    started: list[tuple[str, str]] = []

    async def fake_search(request: YouTubeSearchRequest):
        calls.append(request.max_comments_per_video)
        return [_root("abc123def45")]

    monkeypatch.setattr(youtube_staged, "_exhaustive_youtube_search", fake_search)
    monkeypatch.setattr(
        youtube_staged,
        "_start_background",
        lambda query, video_id: started.append((query, video_id)),
    )
    youtube_staged._BACKGROUND_GENERATIONS.clear()

    events = asyncio.run(
        youtube_staged.youtube_staged_search(
            YouTubeSearchRequest(
                query="https://youtu.be/abc123def45",
                max_videos=1,
                max_comments_per_video=0,
            )
        )
    )

    assert calls == [youtube_staged._FAST_FIRST_REACTIONS]
    assert started == [("https://youtu.be/abc123def45", "abc123def45")]
    assert events[0].public_profile["background_collection_state"] == "running"
    assert events[0].public_profile["collection_mode"] == "fast_first_background_full"
    token = str(events[0].public_profile.get("background_collection_token") or "")
    assert len(token) >= 16
    assert youtube_staged._BACKGROUND_GENERATIONS["abc123def45"] == token


def test_positive_cap_preserves_synchronous_connector_behavior(monkeypatch):
    calls: list[int] = []

    async def fake_search(request: YouTubeSearchRequest):
        calls.append(request.max_comments_per_video)
        return [_root("abc123def45")]

    monkeypatch.setattr(youtube_staged, "_exhaustive_youtube_search", fake_search)

    events = asyncio.run(
        youtube_staged.youtube_staged_search(
            YouTubeSearchRequest(query="RiverLink", max_videos=1, max_comments_per_video=25)
        )
    )

    assert calls == [25]
    assert "background_collection_state" not in events[0].public_profile


def test_wait_for_root_prevents_background_race(monkeypatch):
    checks = iter([False, False, True])
    sleep_calls: list[float] = []

    def fake_match(video_id: str, generation: str) -> bool:
        assert video_id == "abc123def45"
        assert generation == "generation-1"
        return next(checks, True)

    async def fake_sleep(seconds: float):
        sleep_calls.append(seconds)

    monkeypatch.setattr(youtube_staged, "_root_matches", fake_match)
    monkeypatch.setattr(youtube_staged.asyncio, "sleep", fake_sleep)

    ready = asyncio.run(
        youtube_staged._wait_for_root("abc123def45", "generation-1", timeout_seconds=1.0)
    )

    assert ready is True
    assert len(sleep_calls) == 2


def test_cancel_background_tasks_clears_generation_state():
    async def scenario():
        sleeper = asyncio.create_task(asyncio.sleep(30))
        youtube_staged._BACKGROUND_TASKS["abc123def45"] = sleeper
        youtube_staged._BACKGROUND_TASK_GENERATIONS["abc123def45"] = "g1"
        youtube_staged._BACKGROUND_GENERATIONS["abc123def45"] = "g1"
        cancelled = youtube_staged.cancel_youtube_background_tasks()
        await asyncio.sleep(0)
        assert cancelled == 1
        assert sleeper.cancelled()
        assert youtube_staged._BACKGROUND_TASKS == {}
        assert youtube_staged._BACKGROUND_TASK_GENERATIONS == {}
        assert youtube_staged._BACKGROUND_GENERATIONS == {}

    asyncio.run(scenario())
