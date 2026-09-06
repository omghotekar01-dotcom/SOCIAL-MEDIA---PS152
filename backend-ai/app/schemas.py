from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


Platform = Literal[
    "x",
    "telegram",
    "youtube",
    "instagram",
    "facebook",
    "reddit",
    "bluesky",
    "mastodon",
    "replay",
]
SourceMode = Literal["LIVE", "REPLAY", "IMPORT"]


class SocialEventIn(BaseModel):
    platform: Platform
    source_event_id: str
    event_type: str = "post"
    author_platform_id: str | None = None
    author_display: str | None = None
    text: str = ""
    language: str | None = None
    created_at: datetime
    url: str | None = None
    parent_event_id: str | None = None
    conversation_id: str | None = None
    mentions: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)
    engagement: dict[str, int | float | str | None] = Field(default_factory=dict)
    public_profile: dict[str, Any] = Field(default_factory=dict)
    source_mode: SourceMode = "IMPORT"
    connector_run_id: str | None = None

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return " ".join((value or "").split())


class SocialEvent(SocialEventIn):
    id: str = Field(default_factory=lambda: str(uuid4()))
    author_pseudo_id: str | None = None
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_hash: str = ""
    sentiment_label: str | None = None
    sentiment_score: float | None = None
    emotion_scores: dict[str, float] = Field(default_factory=dict)
    stance_label: str | None = None
    stance_confidence: float | None = None
    sarcasm_probability: float | None = None
    topic_terms: list[str] = Field(default_factory=list)
    narrative_cluster_id: str | None = None
    trend_score: float | None = None
    quality_score: float | None = None
    inference_method: str | None = None


class ConnectorStatus(BaseModel):
    platform: str
    state: Literal[
        "READY",
        "LIVE",
        "CREDENTIALS_REQUIRED",
        "PERMISSION_REQUIRED",
        "RATE_LIMITED",
        "NO_CREDITS",
        "DEGRADED",
        "DISABLED",
        "ERROR",
    ]
    detail: str
    source_mode: SourceMode | None = None


class XSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=512)
    max_results: int = Field(default=20, ge=10, le=100)


class TelegramPollRequest(BaseModel):
    max_updates: int = Field(default=50, ge=1, le=100)


class TelegramPublicRequest(BaseModel):
    channel: str = Field(min_length=4, max_length=64)
    limit: int = Field(default=25, ge=1, le=100)


class PublicSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    limit: int = Field(default=25, ge=1, le=100)


class WorkspaceSearchRequest(BaseModel):
    """A fresh analyst search workspace.

    A normal search replaces the previous result pool before collecting the new
    topic, which prevents unrelated searches from colliding in analytics.
    Individual connector buttons can still append evidence afterwards.
    """

    query: str = Field(min_length=1, max_length=300)
    reset: bool = True
    limit_per_source: int = Field(default=15, ge=1, le=40)
    enable_youtube: bool = True
    enable_bluesky: bool = True
    enable_reddit: bool = True
    enable_mastodon: bool = True
    telegram_channel: str | None = Field(default=None, max_length=64)
    instagram_profile: str | None = Field(default=None, max_length=30)


class PublicBridgeRequest(BaseModel):
    query: str = Field(default="", max_length=300)
    target: str = Field(default="", max_length=200)
    limit: int = Field(default=25, ge=1, le=100)


class InstagramPublicRequest(BaseModel):
    profile: str = Field(min_length=1, max_length=30)
    limit: int = Field(default=20, ge=1, le=50)


class InstagramHashtagRequest(BaseModel):
    hashtag: str = Field(min_length=1, max_length=100)
    limit: int = Field(default=25, ge=1, le=50)

    @field_validator("hashtag")
    @classmethod
    def normalize_hashtag(cls, value: str) -> str:
        normalized = value.strip().lstrip("#").strip()
        if not normalized or any(ch.isspace() for ch in normalized):
            raise ValueError("Enter one Instagram hashtag without spaces")
        return normalized


class MastodonSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    limit: int = Field(default=25, ge=1, le=40)
    base_url: str | None = Field(default=None, max_length=300)


class YouTubeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    max_videos: int = Field(default=3, ge=1, le=10)
    max_comments_per_video: int = Field(default=20, ge=1, le=100)


class MetaSyncRequest(BaseModel):
    source: Literal["instagram", "facebook"]
    limit: int = Field(default=25, ge=1, le=100)


class ReplayImportRequest(BaseModel):
    events: list[SocialEventIn]


class DemoSeedRequest(BaseModel):
    reset: bool = True


class AlertOut(BaseModel):
    alert_id: str
    title: str
    severity: str
    narrative_id: str
    triggered_at: datetime
    trend_score: float
    why_triggered: list[str]
    evidence_event_ids: list[str]
    earliest_observed_event_id: str | None = None
    top_amplifiers: list[dict[str, Any]] = Field(default_factory=list)
    platform_mix: dict[str, int] = Field(default_factory=dict)
    sentiment_shift: dict[str, float | str] = Field(default_factory=dict)
    coverage_warning: str | None = None
    confidence: float = 0.0


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
