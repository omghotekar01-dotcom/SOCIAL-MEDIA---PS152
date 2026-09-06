from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from .analytics import assign_clusters, enrich_event
from .connectors import ConnectorError, telegram_poll, x_recent_search, youtube_search
from .db import get_store
from .schemas import XSearchRequest, YouTubeSearchRequest


class CollectorStartRequest(BaseModel):
    query: str = Field(default="#RiverLinkUpdate", min_length=1, max_length=300)
    interval_seconds: int = Field(default=60, ge=60, le=3600)
    enable_telegram: bool = True
    enable_x: bool = False
    enable_youtube: bool = False


class CollectorManager:
    """Small hackathon-safe scheduler for continuous ingestion.

    X and YouTube are opt-in because each call consumes external quota/credits.
    Telegram is enabled by default and remains constrained to chats visible to the
    configured authorized bot. One manager exists per FastAPI process.
    """

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._config: CollectorStartRequest | None = None
        self._last_run_at: datetime | None = None
        self._last_result: dict[str, Any] = {}
        self._cycles = 0

    def status(self) -> dict[str, Any]:
        running = self._task is not None and not self._task.done()
        return {
            "running": running,
            "config": self._config.model_dump() if self._config else None,
            "cycles": self._cycles,
            "last_run_at": self._last_run_at,
            "last_result": self._last_result,
            "note": "X/YouTube continuous polling is opt-in to protect paid credits/quota.",
        }

    async def start(self, config: CollectorStartRequest) -> dict[str, Any]:
        await self.stop()
        self._config = config
        self._stop = asyncio.Event()
        self._cycles = 0
        self._last_result = {}
        self._task = asyncio.create_task(self._loop(), name="nexus-continuous-collector")
        return self.status()

    async def stop(self) -> dict[str, Any]:
        if self._task and not self._task.done():
            self._stop.set()
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        return self.status()

    async def _loop(self) -> None:
        while not self._stop.is_set():
            self._last_result = await self._run_cycle()
            self._last_run_at = datetime.now(timezone.utc)
            self._cycles += 1
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self._config.interval_seconds if self._config else 60)
            except asyncio.TimeoutError:
                continue

    async def _run_cycle(self) -> dict[str, Any]:
        config = self._config or CollectorStartRequest()
        store = get_store()
        report: dict[str, Any] = {"inserted": 0, "platforms": {}}

        async def process(platform: str, coro):
            try:
                events = await coro
                inserted = 0
                duplicates = 0
                for incoming in events:
                    normalized, derived = enrich_event(incoming)
                    row = store.insert(normalized, derived)
                    if row is None:
                        duplicates += 1
                    else:
                        inserted += 1
                report["platforms"][platform] = {
                    "state": "OK",
                    "received": len(events),
                    "inserted": inserted,
                    "duplicates": duplicates,
                }
                report["inserted"] += inserted
            except ConnectorError as exc:
                report["platforms"][platform] = {"state": exc.state, "detail": str(exc)}
            except Exception as exc:  # collector must never kill the service
                report["platforms"][platform] = {"state": "ERROR", "detail": str(exc)[:300]}

        if config.enable_telegram:
            await process("telegram", telegram_poll(100))
        if config.enable_x:
            await process("x", x_recent_search(XSearchRequest(query=config.query, max_results=20)))
        if config.enable_youtube:
            await process(
                "youtube",
                youtube_search(YouTubeSearchRequest(query=config.query, max_videos=2, max_comments_per_video=15)),
            )

        if report["inserted"]:
            assign_clusters(store)
        return report


COLLECTOR = CollectorManager()
