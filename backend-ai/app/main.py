from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .analytics.pipeline import analyze_events
from .config import get_settings
from .connectors import demo as demo_connector
from .connectors import meta as meta_connector
from .connectors import reddit as reddit_connector
from .connectors import telegram as telegram_connector
from .connectors import x as x_connector
from .connectors import youtube as youtube_connector
from .db import store
from .schemas import (
    DemoSeedRequest,
    HealthResponse,
    MetaSyncRequest,
    ReplayImportRequest,
    TelegramPollRequest,
    XSearchRequest,
    YouTubeSearchRequest,
)
from .services.normalizer import normalize_many

settings = get_settings()
app = FastAPI(
    title="NEXUS — Narrative & Influence Intelligence",
    version="0.3.0",
    description=(
        "SIH26152 low-cost multi-platform social-media narrative intelligence API. "
        "Live/replay/import modes are explicitly separated."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def snapshot() -> dict[str, Any]:
    return analyze_events(store.list_events())


def persist_and_report(events, connector_status=None) -> dict[str, Any]:
    count = store.upsert_many(events)
    data = snapshot()
    return {
        "ingested": count,
        "connector_status": connector_status.model_dump(mode="json") if connector_status else None,
        "summary": data["summary"],
    }


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="nexus-analytics-api",
        version="0.3.0",
        environment=settings.nexus_env,
    )


@app.get("/api/platforms/status")
def platform_status() -> dict[str, Any]:
    return {
        "x": x_connector.status().model_dump(mode="json"),
        "telegram": {
            "bot_api": telegram_connector.bot_status().model_dump(mode="json"),
            "mtproto": telegram_connector.mtproto_status().model_dump(mode="json"),
        },
        "youtube": youtube_connector.status().model_dump(mode="json"),
        "instagram": meta_connector.status("instagram").model_dump(mode="json"),
        "facebook": meta_connector.status("facebook").model_dump(mode="json"),
        "reddit": reddit_connector.status().model_dump(mode="json"),
        "replay": {
            "platform": "replay",
            "state": "READY",
            "detail": "Deterministic replay/import is always available and never labelled as live data.",
            "source_mode": "REPLAY",
        },
    }


@app.post("/api/demo/seed")
def seed_demo(request: DemoSeedRequest | None = None) -> dict[str, Any]:
    request = request or DemoSeedRequest()
    if request.reset:
        store.clear()
    events = demo_connector.load_demo_events()
    return persist_and_report(events)


@app.post("/api/import/events")
def import_events(request: ReplayImportRequest) -> dict[str, Any]:
    # User-provided datasets are always relabelled IMPORT so a payload cannot
    # accidentally impersonate live platform ingestion in the UI.
    imported = [event.model_copy(update={"source_mode": "IMPORT"}) for event in request.events]
    normalized = normalize_many(imported)
    return persist_and_report(normalized)


@app.post("/api/ingest/telegram/poll")
def ingest_telegram(request: TelegramPollRequest) -> dict[str, Any]:
    events, status = telegram_connector.poll_bot(request.max_updates)
    return persist_and_report(events, status)


@app.post("/api/ingest/telegram/channel")
async def ingest_telegram_channel(
    channel: str = Body(..., embed=True),
    limit: int = Body(default=50, embed=True),
) -> dict[str, Any]:
    events, status = await telegram_connector.poll_mtproto(channel, limit=max(1, min(limit, 500)))
    return persist_and_report(events, status)


@app.post("/api/ingest/x/search")
def ingest_x(request: XSearchRequest) -> dict[str, Any]:
    events, status = x_connector.search_recent(request.query, request.max_results)
    return persist_and_report(events, status)


@app.post("/api/ingest/x/url")
def ingest_x_url(url: str = Body(..., embed=True)) -> dict[str, Any]:
    events, status = x_connector.import_public_url(url)
    return persist_and_report(events, status)


@app.post("/api/ingest/youtube/search")
def ingest_youtube(request: YouTubeSearchRequest) -> dict[str, Any]:
    events, status = youtube_connector.search_with_comments(
        request.query,
        request.max_videos,
        request.max_comments_per_video,
    )
    return persist_and_report(events, status)


@app.post("/api/ingest/meta/sync")
def ingest_meta(request: MetaSyncRequest) -> dict[str, Any]:
    events, status = meta_connector.sync(request.source, request.limit)
    return persist_and_report(events, status)


@app.post("/api/ingest/reddit/search")
def ingest_reddit(
    query: str = Body(..., embed=True),
    limit: int = Body(default=20, embed=True),
) -> dict[str, Any]:
    events, status = reddit_connector.search(query, max(1, min(limit, 50)))
    return persist_and_report(events, status)


@app.get("/api/dashboard/summary")
def dashboard_summary() -> dict[str, Any]:
    return snapshot()["summary"]


@app.get("/api/events")
def events(
    limit: int = Query(default=500, ge=1, le=5000),
    platform: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    data = analyze_events(store.list_events(limit=limit, platform=platform))
    return data["events"]


@app.delete("/api/events")
def clear_events() -> dict[str, Any]:
    store.clear()
    return {"status": "cleared", "events": 0}


@app.delete("/api/events/{event_id}")
def delete_event(event_id: str) -> dict[str, Any]:
    removed = store.delete_event(event_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"status": "deleted", "event_id": event_id}


@app.get("/api/narratives")
def narratives() -> list[dict[str, Any]]:
    return snapshot()["narratives"]


@app.get("/api/narratives/{narrative_id}")
def narrative(narrative_id: str) -> dict[str, Any]:
    data = snapshot()
    item = next((row for row in data["narratives"] if row["id"] == narrative_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Narrative not found")
    result = dict(item)
    result["events"] = [event for event in data["events"] if event.get("narrative_cluster_id") == narrative_id]
    result["evidence"] = next(
        (row for row in data["evidence"].get("narratives", []) if row["narrative_id"] == narrative_id),
        None,
    )
    result["trend"] = next((row for row in data["trends"] if row["narrative_id"] == narrative_id), None)
    return result


@app.get("/api/narratives/{narrative_id}/timeline")
def narrative_timeline(narrative_id: str) -> list[dict[str, Any]]:
    item = narrative(narrative_id)
    return [
        {
            "id": event["id"],
            "source_event_id": event["source_event_id"],
            "platform": event["platform"],
            "source_mode": event["source_mode"],
            "created_at": event["created_at"],
            "author_display": event.get("author_display"),
            "text": event["text"],
            "sentiment_label": event.get("sentiment_label"),
            "stance_label": event.get("stance_label"),
            "sarcasm_probability": event.get("sarcasm_probability"),
            "url": event.get("url"),
        }
        for event in item["events"]
    ]


@app.get("/api/narratives/{narrative_id}/graph")
def narrative_graph(narrative_id: str) -> dict[str, Any]:
    item = narrative(narrative_id)
    nodes = [
        {
            "id": event["id"],
            "label": event.get("author_display") or event["platform"],
            "platform": event["platform"],
            "created_at": event["created_at"],
            "text": event["text"],
        }
        for event in item["events"]
    ]
    return {"nodes": nodes, "edges": item.get("lineage", []), "narrative_id": narrative_id}


@app.get("/api/trends")
def trends() -> list[dict[str, Any]]:
    return snapshot()["trends"]


@app.get("/api/network")
def network() -> dict[str, Any]:
    return snapshot()["network"]


@app.get("/api/demographics")
def demographics() -> dict[str, Any]:
    return snapshot()["demographics"]


@app.get("/api/alerts")
def alerts() -> list[dict[str, Any]]:
    return snapshot()["alerts"]


@app.get("/api/evidence")
def evidence() -> dict[str, Any]:
    return snapshot()["evidence"]


@app.get("/api/timeline/platforms")
def platform_timeline() -> list[dict[str, Any]]:
    return snapshot()["platform_timeline"]


@app.get("/api/timeline/sentiment")
def sentiment_timeline() -> list[dict[str, Any]]:
    return snapshot()["sentiment_timeline"]


@app.get("/api/export/events.csv")
def export_csv() -> StreamingResponse:
    data = snapshot()["events"]
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id", "source_event_id", "platform", "source_mode", "created_at", "author_display",
            "text", "language", "sentiment", "stance", "sarcasm_probability", "narrative_id", "url",
        ]
    )
    for event in data:
        writer.writerow(
            [
                event["id"], event["source_event_id"], event["platform"], event["source_mode"],
                event["created_at"], event.get("author_display"), event["text"], event.get("language"),
                event.get("sentiment_label"), event.get("stance_label"), event.get("sarcasm_probability"),
                event.get("narrative_cluster_id"), event.get("url"),
            ]
        )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=nexus_events.csv"},
    )
