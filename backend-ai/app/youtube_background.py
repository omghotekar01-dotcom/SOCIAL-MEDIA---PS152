from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from .schemas import SocialEventIn, YouTubeSearchRequest
from .youtube_official import youtube_official_search


IngestFn = Callable[[list[SocialEventIn]], dict[str, Any]]


class YouTubeBackgroundManager:
    """Run exhaustive YouTube conversation collection without blocking Fresh Search.

    The foreground request can ingest a small first sample for immediate analytics,
    while this manager independently collects the provider-bounded exhaustive
    conversation. On completion, duplicates from the foreground sample are ignored
    by the event store and the remaining comments/replies are added to the same
    conversation.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    def _public_job(self, job_id: str) -> dict[str, Any]:
        job = self._jobs.get(job_id)
        if not job:
            return {"job_id": job_id, "state": "NOT_FOUND"}
        return dict(job)

    async def start(self, query: str, ingest_fn: IngestFn) -> dict[str, Any]:
        job_id = f"yt-bg-{uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        self._jobs[job_id] = {
            "job_id": job_id,
            "state": "COLLECTING",
            "query": query,
            "started_at": now,
            "finished_at": None,
            "received": 0,
            "inserted": 0,
            "duplicates": 0,
            "total_events": 0,
            "captured_comment_count": 0,
            "reported_comment_count": 0,
            "collection_complete": False,
            "collection_stop_reason": "running",
            "detail": "Full public YouTube comment/reply crawl is running in the background.",
        }

        async def runner() -> None:
            try:
                events = await youtube_official_search(
                    YouTubeSearchRequest(query=query, max_videos=1, max_comments_per_video=0)
                )
                job = self._jobs[job_id]
                job["state"] = "INGESTING"
                job["received"] = len(events)
                if events:
                    profile = dict(events[0].public_profile or {})
                    job["captured_comment_count"] = int(profile.get("captured_comment_count") or 0)
                    job["reported_comment_count"] = int(profile.get("reported_comment_count") or 0)
                    job["collection_complete"] = bool(profile.get("collection_complete"))
                    job["collection_stop_reason"] = str(profile.get("collection_stop_reason") or "unknown")
                result = await asyncio.to_thread(ingest_fn, events)
                job.update(
                    state="COMPLETE",
                    inserted=int(result.get("inserted", 0)),
                    duplicates=int(result.get("duplicates", 0)),
                    total_events=int(result.get("total_events", 0)),
                    finished_at=datetime.now(timezone.utc).isoformat(),
                    detail=(
                        f"Background crawl finished with {job['captured_comment_count']} public comments/replies captured."
                    ),
                )
            except asyncio.CancelledError:
                job = self._jobs.get(job_id)
                if job:
                    job.update(
                        state="CANCELLED",
                        finished_at=datetime.now(timezone.utc).isoformat(),
                        detail="Background YouTube crawl was cancelled because the analyst workspace changed.",
                    )
                raise
            except Exception as exc:
                job = self._jobs.get(job_id)
                if job:
                    job.update(
                        state="ERROR",
                        finished_at=datetime.now(timezone.utc).isoformat(),
                        collection_complete=False,
                        collection_stop_reason="error",
                        detail=str(exc)[:400],
                    )
            finally:
                self._tasks.pop(job_id, None)

        task = asyncio.create_task(runner(), name=job_id)
        self._tasks[job_id] = task
        return self._public_job(job_id)

    def status(self, job_id: str) -> dict[str, Any]:
        return self._public_job(job_id)

    async def cancel_all(self) -> None:
        tasks = list(self._tasks.values())
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()


YOUTUBE_BACKGROUND = YouTubeBackgroundManager()
