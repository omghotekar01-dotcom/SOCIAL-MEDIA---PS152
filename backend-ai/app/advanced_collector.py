from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Awaitable

from pydantic import BaseModel, Field

from . import free_connectors
from .analytics import assign_clusters, enrich_event
from .config import get_settings
from .connectors import ConnectorError, meta_sync, telegram_poll, x_recent_search, youtube_search
from .db import get_store
from .schemas import MetaSyncRequest, SocialEventIn, XSearchRequest, YouTubeSearchRequest

SETTINGS = get_settings()


class AdvancedCollectorStartRequest(BaseModel):
    query: str = Field(default="#RiverLinkUpdate", min_length=1, max_length=300)
    interval_seconds: int = Field(default=60, ge=60, le=3600)

    # Backward-compatible toggles used by the current frontend.
    enable_telegram: bool = True
    enable_x: bool = False
    enable_youtube: bool = False

    # Free/public continuous sources. These fulfil the SIH continuous collection
    # requirement without burning premium-provider credits.
    enable_telegram_public: bool = True
    enable_bluesky: bool = True
    enable_reddit: bool = True
    enable_mastodon: bool = True
    enable_youtube_free: bool = False

    # Authorized Meta assets are optional and off by default.
    enable_instagram_authorized: bool = False
    enable_facebook_authorized: bool = False


class AdvancedCollectorManager:
    """Continuous, source-aware collection with per-source failure isolation.

    Public/zero-cost sources may run every cycle. X official, YouTube official,
    and Meta-authorized sources remain explicit opt-ins to protect quotas/credits
    and respect provider permissions. One failed provider never kills the loop.
    """

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._config: AdvancedCollectorStartRequest | None = None
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
            "note": (
                "Continuous collection uses Telegram/public + Bluesky + Reddit + Mastodon by default. "
                "Official X/YouTube and authorized Meta polling stay opt-in to protect credits/quota and permissions."
            ),
        }

    async def start(self, config: AdvancedCollectorStartRequest) -> dict[str, Any]:
        await self.stop()
        self._config = config
        self._stop = asyncio.Event()
        self._cycles = 0
        self._last_result = {}
        self._task = asyncio.create_task(self._loop(), name="nexus-continuous-multisource-collector")
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
                await asyncio.wait_for(
                    self._stop.wait(),
                    timeout=self._config.interval_seconds if self._config else 60,
                )
            except asyncio.TimeoutError:
                continue

    async def _run_cycle(self) -> dict[str, Any]:
        config = self._config or AdvancedCollectorStartRequest()
        store = get_store()
        report: dict[str, Any] = {
            "inserted": 0,
            "received": 0,
            "platforms": {},
            "cycle_at": datetime.now(timezone.utc),
            "query": config.query,
        }

        async def process(platform: str, connector: str, awaitable: Awaitable[list[SocialEventIn]]) -> None:
            try:
                events = await awaitable
                inserted = 0
                duplicates = 0
                for incoming in events:
                    profile = dict(incoming.public_profile or {})
                    profile.update(
                        {
                            "connector": connector,
                            "search_query": config.query,
                            "collection_mode": "continuous",
                            "collector_cycle": self._cycles + 1,
                        }
                    )
                    stamped = incoming.model_copy(update={"public_profile": profile})
                    normalized, derived = enrich_event(stamped)
                    row = store.insert(normalized, derived)
                    if row is None:
                        duplicates += 1
                    else:
                        inserted += 1
                report["platforms"][platform] = {
                    "state": "OK",
                    "connector": connector,
                    "received": len(events),
                    "inserted": inserted,
                    "duplicates": duplicates,
                }
                report["received"] += len(events)
                report["inserted"] += inserted
            except ConnectorError as exc:
                report["platforms"][platform] = {"state": exc.state, "connector": connector, "detail": str(exc)}
            except Exception as exc:  # external providers must never kill the collector
                report["platforms"][platform] = {"state": "ERROR", "connector": connector, "detail": str(exc)[:300]}

        jobs: list[tuple[str, str, Awaitable[list[SocialEventIn]]]] = []

        if config.enable_telegram_public:
            channel_spec = f"{SETTINGS.telegram_public_channels or 'NexusSIHDemo'}||{config.query}"
            jobs.append(("telegram_public", "telegram_public_preview", free_connectors.telegram_public_channel(channel_spec, 25)))
        if config.enable_telegram and SETTINGS.telegram_bot_token:
            jobs.append(("telegram_bot", "telegram_bot_api", telegram_poll(100)))
        if config.enable_bluesky:
            jobs.append(("bluesky", "public_atproto_thread", free_connectors.bluesky_search(config.query, 25)))
        if config.enable_reddit:
            jobs.append(("reddit", "reddit_public_or_oauth_comments", free_connectors.reddit_public_search(config.query, 20)))
        if config.enable_mastodon:
            jobs.append(("mastodon", "public_instance_context", free_connectors.mastodon_search(config.query, 20, None)))
        if config.enable_youtube_free:
            jobs.append(("youtube_free", "yt_dlp_public_metadata", free_connectors.youtube_free_search(config.query, 8)))

        # Premium/quota/authorized connectors remain deliberate opt-ins.
        if config.enable_x:
            jobs.append(("x_official", "official_x_api_v2", x_recent_search(XSearchRequest(query=config.query, max_results=20))))
        if config.enable_youtube:
            jobs.append((
                "youtube_official",
                "youtube_data_api_v3",
                youtube_search(YouTubeSearchRequest(query=config.query, max_videos=2, max_comments_per_video=15)),
            ))
        if config.enable_instagram_authorized:
            jobs.append(("instagram", "meta_graph_authorized", meta_sync(MetaSyncRequest(source="instagram", limit=20))))
        if config.enable_facebook_authorized:
            jobs.append(("facebook", "meta_graph_authorized", meta_sync(MetaSyncRequest(source="facebook", limit=20))))

        if jobs:
            await asyncio.gather(*(process(platform, connector, awaitable) for platform, connector, awaitable in jobs))

        if report["inserted"]:
            assign_clusters(store)
        return report
