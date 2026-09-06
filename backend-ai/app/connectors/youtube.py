from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from ..config import get_settings
from ..schemas import ConnectorStatus, SocialEvent, SocialEventIn
from ..services.normalizer import normalize_many

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
COMMENTS_URL = "https://www.googleapis.com/youtube/v3/commentThreads"


def status() -> ConnectorStatus:
    settings = get_settings()
    if not settings.youtube_api_key:
        return ConnectorStatus(
            platform="youtube",
            state="CREDENTIALS_REQUIRED",
            detail="Set YOUTUBE_API_KEY to use the official YouTube Data API v3 free daily quota.",
            source_mode="LIVE",
        )
    return ConnectorStatus(
        platform="youtube",
        state="READY",
        detail="YouTube Data API v3 key configured. Connector caps search/videos/comments to conserve quota.",
        source_mode="LIVE",
    )


def search_with_comments(
    query: str,
    max_videos: int | None = None,
    max_comments_per_video: int | None = None,
) -> tuple[list[SocialEvent], ConnectorStatus]:
    settings = get_settings()
    current = status()
    if current.state != "READY":
        return [], current

    video_limit = max(1, min(max_videos or settings.youtube_max_videos_per_run, settings.youtube_max_videos_per_run, 10))
    comment_limit = max(1, min(max_comments_per_video or settings.youtube_max_comments_per_video, settings.youtube_max_comments_per_video, 100))
    inputs: list[SocialEventIn] = []

    try:
        with httpx.Client(timeout=15) as client:
            search_response = client.get(
                SEARCH_URL,
                params={
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "order": "date",
                    "maxResults": video_limit,
                    "key": settings.youtube_api_key,
                },
            )
            if search_response.status_code == 403:
                return [], _quota_or_permission_status(search_response)
            search_response.raise_for_status()
            search_body = search_response.json()

            for item in search_body.get("items") or []:
                video_id = str((item.get("id") or {}).get("videoId") or "")
                snippet = item.get("snippet") or {}
                if not video_id:
                    continue
                video_event = _video_to_event(video_id, snippet)
                if video_event:
                    inputs.append(video_event)

                comments_response = client.get(
                    COMMENTS_URL,
                    params={
                        "part": "snippet",
                        "videoId": video_id,
                        "maxResults": comment_limit,
                        "order": "time",
                        "textFormat": "plainText",
                        "key": settings.youtube_api_key,
                    },
                )
                # Comments can be disabled per video. Skip that video gracefully.
                if comments_response.status_code in (403, 404):
                    continue
                comments_response.raise_for_status()
                for thread in comments_response.json().get("items") or []:
                    comment_event = _comment_to_event(video_id, thread)
                    if comment_event:
                        inputs.append(comment_event)
    except httpx.HTTPStatusError as exc:
        return [], ConnectorStatus(
            platform="youtube",
            state="ERROR",
            detail=f"YouTube API HTTP {exc.response.status_code}: {exc.response.text[:280]}",
            source_mode="LIVE",
        )
    except Exception as exc:
        return [], ConnectorStatus(
            platform="youtube", state="ERROR", detail=f"YouTube connector error: {exc}", source_mode="LIVE"
        )

    events = normalize_many(inputs)
    return events, ConnectorStatus(
        platform="youtube",
        state="LIVE",
        detail=f"Official YouTube API normalized {len(events)} video/comment events while using capped quota settings.",
        source_mode="LIVE",
    )


def _quota_or_permission_status(response: httpx.Response) -> ConnectorStatus:
    text = response.text.lower()
    if "quota" in text:
        state = "RATE_LIMITED"
        detail = "YouTube Data API quota is exhausted for this key. Replay/import and other connectors continue to work."
    else:
        state = "PERMISSION_REQUIRED"
        detail = "YouTube API key/project cannot perform this request. Check API enablement and key restrictions."
    return ConnectorStatus(platform="youtube", state=state, detail=detail, source_mode="LIVE")


def _parse_time(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _video_to_event(video_id: str, snippet: dict[str, Any]) -> SocialEventIn:
    channel_id = str(snippet.get("channelId") or "unknown")
    title = str(snippet.get("title") or "")
    description = str(snippet.get("description") or "")
    text = f"{title}. {description}".strip()
    return SocialEventIn(
        platform="youtube",
        source_event_id=f"youtube:video:{video_id}",
        event_type="video",
        author_platform_id=channel_id,
        author_display=str(snippet.get("channelTitle") or "YouTube channel"),
        text=text,
        created_at=_parse_time(snippet.get("publishedAt")),
        url=f"https://www.youtube.com/watch?v={video_id}",
        conversation_id=f"youtube:{video_id}",
        public_profile={"channel_id": channel_id},
        source_mode="LIVE",
    )


def _comment_to_event(video_id: str, thread: dict[str, Any]) -> SocialEventIn | None:
    top = ((thread.get("snippet") or {}).get("topLevelComment") or {})
    comment_id = str(top.get("id") or "")
    snippet = top.get("snippet") or {}
    if not comment_id:
        return None
    author_channel = snippet.get("authorChannelId") or {}
    author_id = str(author_channel.get("value") or snippet.get("authorDisplayName") or "unknown")
    return SocialEventIn(
        platform="youtube",
        source_event_id=f"youtube:comment:{comment_id}",
        event_type="video_comment",
        author_platform_id=author_id,
        author_display=str(snippet.get("authorDisplayName") or "YouTube commenter"),
        text=str(snippet.get("textDisplay") or ""),
        created_at=_parse_time(snippet.get("publishedAt")),
        url=f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}",
        parent_event_id=f"youtube:video:{video_id}",
        conversation_id=f"youtube:{video_id}",
        engagement={"likes": int(snippet.get("likeCount") or 0)},
        public_profile={},
        source_mode="LIVE",
    )
