from __future__ import annotations

from uuid import uuid4

import httpx

from .config import get_settings
from .connectors import ConnectorError, _parse_dt
from .schemas import SocialEventIn, YouTubeSearchRequest

SETTINGS = get_settings()


async def youtube_official_search(request: YouTubeSearchRequest) -> list[SocialEventIn]:
    """Official YouTube Data API v3 search with video-first resilience.

    Every successful search result is normalized as a video event before comment
    collection is attempted. A video with comments disabled therefore still
    contributes timestamped public evidence instead of making the connector look
    empty.
    """
    key = SETTINGS.youtube_api_key
    if not key:
        raise ConnectorError("YouTube API key is not configured.", "CREDENTIALS_REQUIRED")

    run_id = f"yt-{uuid4().hex[:10]}"
    max_videos = min(request.max_videos, SETTINGS.youtube_max_videos_per_run, 10)
    max_comments = min(request.max_comments_per_video, SETTINGS.youtube_max_comments_per_video, 100)
    output: list[SocialEventIn] = []

    async with httpx.AsyncClient(timeout=20) as client:
        search_resp = await client.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "key": key,
                "part": "snippet",
                "q": request.query,
                "type": "video",
                "order": "date",
                "maxResults": max_videos,
            },
        )
        if search_resp.status_code == 429:
            raise ConnectorError("YouTube API rate limit reached.", "RATE_LIMITED")
        if search_resp.status_code == 403:
            raise ConnectorError("YouTube API quota/permission error. Check key and quota.", "RATE_LIMITED")
        if search_resp.status_code in {400, 401}:
            raise ConnectorError("YouTube API key/request is invalid.", "CREDENTIALS_REQUIRED")
        if search_resp.status_code >= 400:
            raise ConnectorError(f"YouTube search error {search_resp.status_code}: {search_resp.text[:300]}", "DEGRADED")

        for item in search_resp.json().get("items", []):
            video_id = str((item.get("id") or {}).get("videoId") or "")
            snippet = item.get("snippet") or {}
            if not video_id:
                continue

            title = str(snippet.get("title") or "").strip()
            description = str(snippet.get("description") or "").strip()
            video_text = " — ".join(part for part in [title, description] if part).strip()
            channel_id = str(snippet.get("channelId") or "") or None
            channel_title = str(snippet.get("channelTitle") or "") or None

            # Always retain the video result itself, even if comments are disabled.
            output.append(
                SocialEventIn(
                    platform="youtube",
                    source_event_id=f"video:{video_id}",
                    event_type="video",
                    author_platform_id=channel_id,
                    author_display=channel_title,
                    text=video_text or title or f"YouTube video {video_id}",
                    created_at=_parse_dt(snippet.get("publishedAt")),
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    conversation_id=video_id,
                    engagement={},
                    public_profile={"collection_scope": "official_video_search"},
                    source_mode="LIVE",
                    connector_run_id=run_id,
                )
            )

            comments_resp = await client.get(
                "https://www.googleapis.com/youtube/v3/commentThreads",
                params={
                    "key": key,
                    "part": "snippet,replies",
                    "videoId": video_id,
                    "textFormat": "plainText",
                    "maxResults": max_comments,
                    "order": "time",
                },
            )
            if comments_resp.status_code in {403, 404}:
                # Disabled/restricted comments are normal; the video event remains.
                continue
            if comments_resp.status_code == 429:
                # Keep already collected video evidence rather than failing the run.
                continue
            if comments_resp.status_code >= 400:
                continue

            for thread in comments_resp.json().get("items", []):
                top = (thread.get("snippet") or {}).get("topLevelComment") or {}
                comment = top.get("snippet") or {}
                comment_id = str(top.get("id") or thread.get("id") or "")
                text = str(comment.get("textDisplay") or comment.get("textOriginal") or "").strip()
                if not comment_id or not text:
                    continue
                output.append(
                    SocialEventIn(
                        platform="youtube",
                        source_event_id=f"comment:{comment_id}",
                        event_type="video_comment",
                        author_platform_id=(comment.get("authorChannelId") or {}).get("value"),
                        author_display=comment.get("authorDisplayName"),
                        text=text,
                        created_at=_parse_dt(comment.get("publishedAt")),
                        url=f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}",
                        parent_event_id=f"video:{video_id}",
                        conversation_id=video_id,
                        engagement={"likes": comment.get("likeCount", 0)},
                        public_profile={"collection_scope": "official_comment_thread"},
                        source_mode="LIVE",
                        connector_run_id=run_id,
                    )
                )
    return output
