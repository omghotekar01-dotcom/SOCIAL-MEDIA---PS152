from __future__ import annotations

import asyncio
import csv
import io
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from .analytics import (
    alerts,
    assign_clusters,
    build_network,
    demographics,
    enrich_event,
    narrative_summaries,
    overview,
    seed_demo_events,
    timeline,
)
from .certificates import build_narrative_certificate, certificate_summary
from .collector import COLLECTOR, CollectorStartRequest
from .config import get_settings
from .connectors import ConnectorError, connector_statuses, meta_sync, telegram_poll, x_recent_search, youtube_search
from .db import get_store
from .free_connectors import (
    bluesky_search,
    instagram_public_profile,
    mastodon_search,
    reddit_public_search,
    telegram_public_channel,
    x_public_bridge,
    youtube_free_search,
)
from .meta_discovery import instagram_hashtag_search
from .schemas import (
    ConnectorStatus,
    DemoSeedRequest,
    HealthResponse,
    InstagramHashtagRequest,
    InstagramPublicRequest,
    MastodonSearchRequest,
    MetaSyncRequest,
    PublicBridgeRequest,
    PublicSearchRequest,
    ReplayImportRequest,
    SocialEvent,
    SocialEventIn,
    TelegramPollRequest,
    TelegramPublicRequest,
    WorkspaceSearchRequest,
    XSearchRequest,
    YouTubeSearchRequest,
)

SETTINGS = get_settings()
STORE = get_store()

app = FastAPI(
    title="NEXUS — Narrative & Influence Intelligence",
    description="SIH26152 social-media analytics engine with evidence-aware narrative lineage and free/public-source fallbacks.",
    version="0.4.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=SETTINGS.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _stamp_events(
    events: list[SocialEventIn],
    *,
    connector: str,
    search_query: str | None = None,
    search_session_id: str | None = None,
) -> list[SocialEventIn]:
    stamped: list[SocialEventIn] = []
    for event in events:
        profile = dict(event.public_profile or {})
        profile["connector"] = connector
        if search_query:
            profile["search_query"] = search_query
        if search_session_id:
            profile["search_session_id"] = search_session_id
        stamped.append(event.model_copy(update={"public_profile": profile}))
    return stamped


def ingest(events: list[SocialEventIn]) -> dict[str, Any]:
    inserted: list[SocialEvent] = []
    duplicates = 0
    for incoming in events:
        normalized, derived = enrich_event(incoming)
        row = STORE.insert(normalized, derived)
        if row is None:
            duplicates += 1
        else:
            inserted.append(row)
    if inserted:
        assign_clusters(STORE)
    return {
        "received": len(events),
        "inserted": len(inserted),
        "duplicates": duplicates,
        "event_ids": [e.id for e in inserted],
        "total_events": STORE.count(),
    }


def connector_exception(exc: ConnectorError) -> HTTPException:
    status_code = 429 if exc.state == "RATE_LIMITED" else 503
    if exc.state == "ERROR":
        status_code = 400
    return HTTPException(status_code=status_code, detail={"state": exc.state, "message": str(exc)})


def enhanced_connector_statuses() -> list[ConnectorStatus]:
    """Expose official access and free fallbacks without pretending degraded access is equivalent."""
    base = {item.platform: item for item in connector_statuses()}

    if not SETTINGS.x_bearer_token:
        base["x"] = ConnectorStatus(
            platform="x",
            state="DEGRADED" if SETTINGS.x_public_rss_url_template else "CREDENTIALS_REQUIRED",
            detail=(
                "Configured permitted RSS/public bridge is available; official X API remains the preferred richer path."
                if SETTINGS.x_public_rss_url_template
                else "Official recent-search requires X developer access/credits. Replay/import remains available; optionally configure a permitted X_PUBLIC_RSS_URL_TEMPLATE."
            ),
            source_mode="LIVE" if SETTINGS.x_public_rss_url_template else "IMPORT",
        )

    base["telegram"] = ConnectorStatus(
        platform="telegram",
        state="READY",
        detail=(
            "Bot API live ingestion is configured, and zero-key public-channel preview ingestion is also available."
            if SETTINGS.telegram_bot_token
            else "Zero-key public-channel preview ingestion is ready. Bot API is an additional free path for chats visible to an authorized bot."
        ),
        source_mode="LIVE",
    )

    if not SETTINGS.youtube_api_key:
        base["youtube"] = ConnectorStatus(
            platform="youtube",
            state="DEGRADED",
            detail="Zero-key yt-dlp public video-metadata search is available. Add a YouTube Data API key for richer official search/comment ingestion.",
            source_mode="LIVE",
        )

    if SETTINGS.meta_access_token and SETTINGS.meta_instagram_account_id:
        base["instagram"] = ConnectorStatus(
            platform="instagram",
            state="READY",
            detail="Meta Graph credentials configured for authorized account sync and official public hashtag discovery where the app has Instagram Public Content Access.",
            source_mode="LIVE",
        )
    else:
        base["instagram"] = ConnectorStatus(
            platform="instagram",
            state="DEGRADED",
            detail="Best-effort public-profile fallback is available for genuinely public profiles; official Meta Graph access is preferred for stable account and hashtag data.",
            source_mode="LIVE",
        )

    base["bluesky"] = ConnectorStatus(
        platform="bluesky",
        state="READY",
        detail="Public AT Protocol search is available without credentials.",
        source_mode="LIVE",
    )
    base["reddit"] = ConnectorStatus(
        platform="reddit",
        state="DEGRADED",
        detail="Low-volume public JSON search is attempted where Reddit permits it; OAuth/import remains the fallback if restricted.",
        source_mode="LIVE",
    )
    base["mastodon"] = ConnectorStatus(
        platform="mastodon",
        state="DEGRADED",
        detail=f"Public instance search targets {SETTINGS.mastodon_base_url}; availability depends on the selected instance policy.",
        source_mode="LIVE",
    )
    return list(base.values())


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {
        "name": "NEXUS — Narrative & Influence Intelligence",
        "sih_problem": "SIH26152 — Social Media Analytics",
        "status": "ready",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="nexus-ai", version="0.4.0", environment=SETTINGS.nexus_env)


@app.get("/api/connectors/status", tags=["connectors"])
def get_connector_statuses():
    return {"connectors": enhanced_connector_statuses()}


@app.get("/api/collector/status", tags=["collector"])
def collector_status():
    return COLLECTOR.status()


@app.post("/api/collector/start", tags=["collector"])
async def collector_start(request: CollectorStartRequest):
    return await COLLECTOR.start(request)


@app.post("/api/collector/stop", tags=["collector"])
async def collector_stop():
    return await COLLECTOR.stop()


@app.post("/api/workspace/reset", tags=["workspace"])
async def workspace_reset():
    """Clear the active analyst result pool without seeding replacement data."""
    await COLLECTOR.stop()
    STORE.reset()
    return {"status": "cleared", "total_events": 0}


@app.post("/api/search/workspace", tags=["workspace"])
async def workspace_search(request: WorkspaceSearchRequest):
    """Create a clean search workspace and collect independent low-cost sources.

    This is the default analyst search path. By resetting before a new query,
    analytics for one topic cannot collide with results from a previous topic.
    Connector failures are reported per source and do not discard successful
    evidence from other sources.
    """
    if request.reset:
        await COLLECTOR.stop()
        STORE.reset()

    session_id = f"search-{uuid4().hex[:12]}"
    limit = request.limit_per_source
    jobs: list[tuple[str, str, Any]] = []

    if request.enable_youtube:
        jobs.append(("youtube", "yt_dlp_public_metadata", youtube_free_search(request.query, min(limit, 25))))
    if request.enable_bluesky:
        jobs.append(("bluesky", "public_atproto", bluesky_search(request.query, limit)))
    if request.enable_reddit:
        jobs.append(("reddit", "public_json", reddit_public_search(request.query, limit)))
    if request.enable_mastodon:
        jobs.append(("mastodon", "public_instance_api", mastodon_search(request.query, min(limit, 40), None)))
    if request.telegram_channel:
        jobs.append(("telegram", "telegram_public_preview", telegram_public_channel(request.telegram_channel, limit)))
    if request.instagram_profile:
        jobs.append(("instagram", "instaloader_public_profile", instagram_public_profile(request.instagram_profile, min(limit, 20))))

    results = await asyncio.gather(*(job[2] for job in jobs), return_exceptions=True)
    collected: list[SocialEventIn] = []
    sources: dict[str, Any] = {}

    for (platform, connector, _), result in zip(jobs, results):
        if isinstance(result, Exception):
            state = result.state if isinstance(result, ConnectorError) else "ERROR"
            sources[platform] = {"state": state, "received": 0, "detail": str(result)[:300]}
            continue
        stamped = _stamp_events(
            result,
            connector=connector,
            search_query=request.query,
            search_session_id=session_id,
        )
        collected.extend(stamped)
        sources[platform] = {"state": "OK", "received": len(stamped), "connector": connector}

    ingest_result = ingest(collected) if collected else {
        "received": 0,
        "inserted": 0,
        "duplicates": 0,
        "event_ids": [],
        "total_events": STORE.count(),
    }
    return {
        **ingest_result,
        "query": request.query,
        "search_session_id": session_id,
        "reset": request.reset,
        "sources": sources,
        "message": "Fresh search workspace loaded; previous query results were cleared." if request.reset else "Search evidence appended to current workspace.",
    }


@app.post("/api/demo/seed", tags=["demo"])
def seed_demo(request: DemoSeedRequest):
    if request.reset:
        STORE.reset()
    events = _stamp_events(seed_demo_events(), connector="deterministic_replay", search_query="#RiverLinkUpdate", search_session_id="demo-seed-v1")
    result = ingest(events)
    result["message"] = "Deterministic fictional demo dataset loaded. Replay/import/live source labels remain explicit."
    return result


@app.post("/api/ingest/replay", tags=["ingestion"])
def ingest_replay(request: ReplayImportRequest):
    safe_events: list[SocialEventIn] = []
    for event in request.events:
        mode = "REPLAY" if event.source_mode == "REPLAY" else "IMPORT"
        safe_events.append(event.model_copy(update={"source_mode": mode}))
    return ingest(_stamp_events(safe_events, connector="user_import"))


@app.post("/api/connectors/x/search", tags=["connectors"])
async def ingest_x(request: XSearchRequest):
    try:
        events = await x_recent_search(request)
    except ConnectorError as exc:
        raise connector_exception(exc) from exc
    result = ingest(_stamp_events(events, connector="official_x_api_v2", search_query=request.query))
    result.update(platform="x", source_mode="LIVE", connector="official_x_api_v2")
    return result


@app.post("/api/connectors/x/public", tags=["connectors"])
async def ingest_x_public(request: PublicBridgeRequest):
    if not request.query.strip() and not request.target.strip():
        raise HTTPException(status_code=400, detail="Provide query or target for the configured X public bridge.")
    try:
        events = await x_public_bridge(request.query, request.target, request.limit)
    except ConnectorError as exc:
        raise connector_exception(exc) from exc
    result = ingest(_stamp_events(events, connector="configured_public_bridge", search_query=request.query or request.target))
    result.update(platform="x", source_mode="LIVE", connector="configured_public_bridge")
    return result


@app.post("/api/connectors/telegram/poll", tags=["connectors"])
async def ingest_telegram(request: TelegramPollRequest):
    try:
        events = await telegram_poll(request.max_updates)
    except ConnectorError as exc:
        raise connector_exception(exc) from exc
    result = ingest(_stamp_events(events, connector="telegram_bot_api"))
    result.update(platform="telegram", source_mode="LIVE", connector="telegram_bot_api")
    return result


@app.post("/api/connectors/telegram/public", tags=["connectors"])
async def ingest_telegram_public(request: TelegramPublicRequest):
    try:
        events = await telegram_public_channel(request.channel, request.limit)
    except ConnectorError as exc:
        raise connector_exception(exc) from exc
    result = ingest(_stamp_events(events, connector="telegram_public_preview", search_query=request.channel))
    result.update(platform="telegram", source_mode="LIVE", connector="telegram_public_preview")
    return result


@app.post("/api/connectors/youtube/search", tags=["connectors"])
async def ingest_youtube(request: YouTubeSearchRequest):
    try:
        events = await youtube_search(request)
    except ConnectorError as exc:
        raise connector_exception(exc) from exc
    result = ingest(_stamp_events(events, connector="youtube_data_api_v3", search_query=request.query))
    result.update(platform="youtube", source_mode="LIVE", connector="youtube_data_api_v3")
    return result


@app.post("/api/connectors/youtube/free", tags=["connectors"])
async def ingest_youtube_free(request: PublicSearchRequest):
    try:
        events = await youtube_free_search(request.query, min(request.limit, 25))
    except ConnectorError as exc:
        raise connector_exception(exc) from exc
    result = ingest(_stamp_events(events, connector="yt_dlp_public_metadata", search_query=request.query))
    result.update(platform="youtube", source_mode="LIVE", connector="yt_dlp_public_metadata")
    return result


@app.post("/api/connectors/meta/sync", tags=["connectors"])
async def ingest_meta(request: MetaSyncRequest):
    try:
        events = await meta_sync(request)
    except ConnectorError as exc:
        raise connector_exception(exc) from exc
    result = ingest(_stamp_events(events, connector="meta_graph_api"))
    result.update(platform=request.source, source_mode="LIVE", connector="meta_graph_api")
    return result


@app.post("/api/connectors/instagram/hashtag", tags=["connectors"])
async def ingest_instagram_hashtag(request: InstagramHashtagRequest):
    try:
        events = await instagram_hashtag_search(request.hashtag, request.limit)
    except ConnectorError as exc:
        raise connector_exception(exc) from exc
    result = ingest(_stamp_events(events, connector="meta_graph_hashtag_recent_media", search_query=f"#{request.hashtag}"))
    result.update(platform="instagram", source_mode="LIVE", connector="meta_graph_hashtag_recent_media")
    return result


@app.post("/api/connectors/instagram/public", tags=["connectors"])
async def ingest_instagram_public(request: InstagramPublicRequest):
    try:
        events = await instagram_public_profile(request.profile, request.limit)
    except ConnectorError as exc:
        raise connector_exception(exc) from exc
    result = ingest(_stamp_events(events, connector="instaloader_public_profile", search_query=request.profile))
    result.update(platform="instagram", source_mode="LIVE", connector="instaloader_public_profile")
    return result


@app.post("/api/connectors/bluesky/search", tags=["connectors"])
async def ingest_bluesky(request: PublicSearchRequest):
    try:
        events = await bluesky_search(request.query, request.limit)
    except ConnectorError as exc:
        raise connector_exception(exc) from exc
    result = ingest(_stamp_events(events, connector="public_atproto", search_query=request.query))
    result.update(platform="bluesky", source_mode="LIVE", connector="public_atproto")
    return result


@app.post("/api/connectors/reddit/search", tags=["connectors"])
async def ingest_reddit(request: PublicSearchRequest):
    try:
        events = await reddit_public_search(request.query, request.limit)
    except ConnectorError as exc:
        raise connector_exception(exc) from exc
    result = ingest(_stamp_events(events, connector="public_json", search_query=request.query))
    result.update(platform="reddit", source_mode="LIVE", connector="public_json")
    return result


@app.post("/api/connectors/mastodon/search", tags=["connectors"])
async def ingest_mastodon(request: MastodonSearchRequest):
    try:
        events = await mastodon_search(request.query, request.limit, request.base_url)
    except ConnectorError as exc:
        raise connector_exception(exc) from exc
    result = ingest(_stamp_events(events, connector="public_instance_api", search_query=request.query))
    result.update(platform="mastodon", source_mode="LIVE", connector="public_instance_api")
    return result


@app.get("/api/overview", tags=["analytics"])
def api_overview():
    return overview(STORE)


@app.get("/api/timeline", tags=["analytics"])
def api_timeline(minutes: int = Query(default=15, ge=5, le=120)):
    return {"bucket_minutes": minutes, "points": timeline(STORE.list_events(limit=5000), minutes)}


@app.get("/api/trends", tags=["analytics"])
def api_trends():
    return {"narratives": narrative_summaries(STORE)}


@app.get("/api/narratives", tags=["analytics"])
def api_narratives():
    return {"narratives": narrative_summaries(STORE)}


@app.get("/api/narratives/{narrative_id}", tags=["analytics"])
def api_narrative_detail(narrative_id: str):
    narratives = {n["id"]: n for n in narrative_summaries(STORE)}
    narrative = narratives.get(narrative_id)
    if not narrative:
        raise HTTPException(status_code=404, detail="Narrative not found")
    events = STORE.list_events(limit=5000, narrative_id=narrative_id)
    network = build_network(STORE.list_events(limit=5000), narrative_id)
    chronological = sorted(events, key=lambda e: e.created_at)
    return {
        **narrative,
        "events": chronological,
        "network": network,
        "lineage": [
            {
                "event_id": e.id,
                "platform": e.platform,
                "source_mode": e.source_mode,
                "created_at": e.created_at,
                "author": e.author_display,
                "author_pseudo_id": e.author_pseudo_id,
                "text": e.text,
                "sentiment": e.sentiment_label,
                "stance": e.stance_label,
                "source_url": e.url,
                "engagement": e.engagement,
                "public_profile": e.public_profile,
            }
            for e in chronological
        ],
        "origin_claim": "Earliest observed event in the configured/collected dataset; not a claim of absolute internet origin.",
    }


@app.get("/api/network", tags=["analytics"])
def api_network(narrative_id: str | None = None):
    assign_clusters(STORE)
    return build_network(STORE.list_events(limit=5000), narrative_id)


@app.get("/api/demographics", tags=["analytics"])
def api_demographics():
    return demographics(STORE.list_events(limit=5000))


@app.get("/api/alerts", tags=["analytics"])
def api_alerts():
    return {"alerts": alerts(STORE)}


@app.get("/api/certificates", tags=["evidence-certificate"])
def api_certificates():
    certificates = []
    for narrative in narrative_summaries(STORE):
        certificate = build_narrative_certificate(STORE, narrative["id"])
        if certificate:
            certificates.append(certificate_summary(certificate))
    return {"certificates": certificates, "policy": "No certificate => ABSTAIN for high-severity narrative claims."}


@app.get("/api/certificates/narrative/{narrative_id}", tags=["evidence-certificate"])
def api_narrative_certificate(narrative_id: str):
    certificate = build_narrative_certificate(STORE, narrative_id)
    if not certificate:
        raise HTTPException(status_code=404, detail="Narrative not found; no evidence certificate can be issued.")
    return certificate


@app.get("/api/certificates/alert/{alert_id}", tags=["evidence-certificate"])
def api_alert_certificate(alert_id: str):
    alert_match = None
    for item in alerts(STORE):
        item_id = getattr(item, "alert_id", None) if not isinstance(item, dict) else item.get("alert_id")
        if item_id == alert_id:
            alert_match = item
            break
    if alert_match is None:
        raise HTTPException(status_code=404, detail="Alert not found; ABSTAIN.")
    narrative_id = getattr(alert_match, "narrative_id", None) if not isinstance(alert_match, dict) else alert_match.get("narrative_id")
    certificate = build_narrative_certificate(STORE, str(narrative_id))
    if not certificate:
        raise HTTPException(status_code=409, detail={"decision": "ABSTAIN", "reason": "Insufficient replayable evidence for this alert."})
    certificate["alert_id"] = alert_id
    return certificate


@app.get("/api/events", tags=["evidence"])
def api_events(
    limit: int = Query(default=250, ge=1, le=2000),
    platform: str | None = None,
    narrative_id: str | None = None,
    newest_first: bool = False,
):
    return {
        "events": STORE.list_events(
            limit=limit,
            platform=platform,
            narrative_id=narrative_id,
            newest_first=newest_first,
        )
    }


@app.get("/api/events/{event_id}", tags=["evidence"])
def api_event(event_id: str):
    event = STORE.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@app.get("/api/export/narrative/{narrative_id}.json", tags=["export"])
def export_narrative_json(narrative_id: str):
    events = STORE.list_events(limit=5000, narrative_id=narrative_id)
    if not events:
        raise HTTPException(status_code=404, detail="Narrative not found")
    return {
        "generated_at": datetime.now(timezone.utc),
        "narrative_id": narrative_id,
        "scope_note": "Earliest observed means earliest in collected data. LIVE/REPLAY/IMPORT labels are preserved.",
        "events": [e.model_dump(mode="json") for e in events],
    }


@app.get("/api/export/narrative/{narrative_id}.csv", tags=["export"])
def export_narrative_csv(narrative_id: str):
    events = STORE.list_events(limit=5000, narrative_id=narrative_id)
    if not events:
        raise HTTPException(status_code=404, detail="Narrative not found")
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "id",
            "platform",
            "source_mode",
            "source_event_id",
            "created_at",
            "author_pseudo_id",
            "author_display",
            "text",
            "sentiment_label",
            "sentiment_score",
            "stance_label",
            "stance_confidence",
            "narrative_cluster_id",
            "url",
        ],
    )
    writer.writeheader()
    for event in events:
        writer.writerow({field: getattr(event, field) for field in writer.fieldnames})
    filename = f"nexus-{narrative_id}.csv"
    return Response(
        buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
