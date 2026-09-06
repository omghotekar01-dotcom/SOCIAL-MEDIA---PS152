from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any

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
from .config import get_settings
from .connectors import ConnectorError, connector_statuses, meta_sync, telegram_poll, x_recent_search, youtube_search
from .db import get_store
from .schemas import (
    DemoSeedRequest,
    HealthResponse,
    MetaSyncRequest,
    ReplayImportRequest,
    SocialEvent,
    SocialEventIn,
    TelegramPollRequest,
    XSearchRequest,
    YouTubeSearchRequest,
)


SETTINGS = get_settings()
STORE = get_store()

app = FastAPI(
    title="NEXUS — Narrative & Influence Intelligence",
    description="SIH26152 social-media analytics engine with evidence-aware narrative lineage.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=SETTINGS.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    return HTTPException(status_code=status_code, detail={"state": exc.state, "message": str(exc)})


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
    return HealthResponse(status="ok", service="nexus-ai", version="0.1.0", environment=SETTINGS.nexus_env)


@app.get("/api/connectors/status", tags=["connectors"])
def get_connector_statuses():
    return {"connectors": connector_statuses()}


@app.post("/api/demo/seed", tags=["demo"])
def seed_demo(request: DemoSeedRequest):
    if request.reset:
        STORE.reset()
    events = seed_demo_events()
    result = ingest(events)
    result["message"] = "Deterministic fictional demo dataset loaded. X-style records are labelled REPLAY."
    return result


@app.post("/api/ingest/replay", tags=["ingestion"])
def ingest_replay(request: ReplayImportRequest):
    safe_events: list[SocialEventIn] = []
    for event in request.events:
        # User-supplied/import endpoint must never be able to mark imported records as live.
        mode = "REPLAY" if event.source_mode == "REPLAY" else "IMPORT"
        safe_events.append(event.model_copy(update={"source_mode": mode}))
    return ingest(safe_events)


@app.post("/api/connectors/x/search", tags=["connectors"])
async def ingest_x(request: XSearchRequest):
    try:
        events = await x_recent_search(request)
    except ConnectorError as exc:
        raise connector_exception(exc) from exc
    result = ingest(events)
    result["platform"] = "x"
    result["source_mode"] = "LIVE"
    return result


@app.post("/api/connectors/telegram/poll", tags=["connectors"])
async def ingest_telegram(request: TelegramPollRequest):
    try:
        events = await telegram_poll(request.max_updates)
    except ConnectorError as exc:
        raise connector_exception(exc) from exc
    result = ingest(events)
    result["platform"] = "telegram"
    result["source_mode"] = "LIVE"
    return result


@app.post("/api/connectors/youtube/search", tags=["connectors"])
async def ingest_youtube(request: YouTubeSearchRequest):
    try:
        events = await youtube_search(request)
    except ConnectorError as exc:
        raise connector_exception(exc) from exc
    result = ingest(events)
    result["platform"] = "youtube"
    result["source_mode"] = "LIVE"
    return result


@app.post("/api/connectors/meta/sync", tags=["connectors"])
async def ingest_meta(request: MetaSyncRequest):
    try:
        events = await meta_sync(request)
    except ConnectorError as exc:
        raise connector_exception(exc) from exc
    result = ingest(events)
    result["platform"] = request.source
    result["source_mode"] = "LIVE"
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
    payload = {
        "generated_at": datetime.now(timezone.utc),
        "narrative_id": narrative_id,
        "scope_note": "Earliest observed means earliest in collected data. LIVE/REPLAY/IMPORT labels are preserved.",
        "events": [e.model_dump(mode="json") for e in events],
    }
    return payload


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
    for e in events:
        writer.writerow({field: getattr(e, field) for field in writer.fieldnames})
    filename = f"nexus-{narrative_id}.csv"
    return Response(
        buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
