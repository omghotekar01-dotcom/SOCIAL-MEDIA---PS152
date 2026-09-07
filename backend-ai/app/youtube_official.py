from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

import httpx

from .config import get_settings
from .connectors import ConnectorError, _parse_dt
from .schemas import SocialEventIn, YouTubeSearchRequest

SETTINGS = get_settings()

_YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YOUTUBE_URL_RES = [
    re.compile(r"(?:youtube\.com/watch\?(?:[^#\s]*&)?v=)([A-Za-z0-9_-]{11})", re.I),
    re.compile(r"(?:youtu\.be/)([A-Za-z0-9_-]{11})", re.I),
    re.compile(r"(?:youtube\.com/(?:shorts|live|embed)/)([A-Za-z0-9_-]{11})", re.I),
]


def _thumbnail(snippet: dict[str, Any]) -> str | None:
    thumbnails = snippet.get("thumbnails") or {}
    for key in ("maxres", "standard", "high", "medium", "default"):
        url = (thumbnails.get(key) or {}).get("url")
        if url:
            return str(url)
    return None


def _extract_video_id(value: str) -> str | None:
    clean = (value or "").strip()
    if _YOUTUBE_ID_RE.fullmatch(clean):
        return clean
    for pattern in _YOUTUBE_URL_RES:
        match = pattern.search(clean)
        if match:
            return match.group(1)
    return None


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _error_reason(response: httpx.Response) -> str:
    try:
        payload = response.json()
        errors = ((payload.get("error") or {}).get("errors") or [])
        if errors:
            return str(errors[0].get("reason") or errors[0].get("message") or "")
        return str((payload.get("error") or {}).get("message") or "")
    except Exception:
        return ""


def _comment_event(
    *,
    video_id: str,
    raw: dict[str, Any],
    root_parent: str,
    run_id: str,
    thumb: str | None,
    is_reply: bool,
) -> SocialEventIn | None:
    snippet = raw.get("snippet") or {}
    comment_id = str(raw.get("id") or "")
    text = str(snippet.get("textDisplay") or snippet.get("textOriginal") or "").strip()
    if not comment_id or not text:
        return None

    return SocialEventIn(
        platform="youtube",
        source_event_id=(f"reply:{comment_id}" if is_reply else f"comment:{comment_id}"),
        event_type="video_comment_reply" if is_reply else "video_comment",
        author_platform_id=(snippet.get("authorChannelId") or {}).get("value"),
        author_display=snippet.get("authorDisplayName"),
        text=text,
        created_at=_parse_dt(snippet.get("publishedAt")),
        url=f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}",
        parent_event_id=root_parent,
        conversation_id=video_id,
        engagement={"likes": _int(snippet.get("likeCount"))},
        public_profile={
            "collection_scope": "official_comment_reply" if is_reply else "official_comment_thread",
            "avatar_url": snippet.get("authorProfileImageUrl"),
            "media_kind": "video_context",
            "thumbnail_url": thumb,
            "embed_url": f"https://www.youtube.com/embed/{video_id}",
            "video_id": video_id,
            "updated_at": snippet.get("updatedAt"),
        },
        source_mode="LIVE",
        connector_run_id=run_id,
    )


async def _video_details(client: httpx.AsyncClient, key: str, video_ids: list[str]) -> list[dict[str, Any]]:
    if not video_ids:
        return []
    response = await client.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={
            "key": key,
            "part": "snippet,statistics,status",
            "id": ",".join(video_ids[:50]),
            "maxResults": min(len(video_ids), 50),
        },
    )
    if response.status_code == 429:
        raise ConnectorError("YouTube API rate limit reached while reading video metadata.", "RATE_LIMITED")
    if response.status_code == 403:
        reason = _error_reason(response)
        raise ConnectorError(f"YouTube API quota/permission error while reading videos{f': {reason}' if reason else ''}.", "RATE_LIMITED")
    if response.status_code in {400, 401}:
        raise ConnectorError("YouTube API key/request is invalid.", "CREDENTIALS_REQUIRED")
    if response.status_code >= 400:
        raise ConnectorError(f"YouTube videos.list error {response.status_code}: {response.text[:300]}", "DEGRADED")
    return list(response.json().get("items", []))


async def youtube_official_search(request: YouTubeSearchRequest) -> list[SocialEventIn]:
    """Official YouTube Data API v3 video + comment/reply ingestion.

    Prototype reliability improvements:
    - accepts an exact YouTube URL/video id, bypassing search entirely;
    - query search looks at a wider candidate set and prioritizes videos that
      actually report comments instead of blindly choosing the newest uploads;
    - keeps the root video even if comments are disabled;
    - ingests top-level comments plus nested replies, fetching comments.list when
      commentThreads only includes a reply subset.
    """
    key = SETTINGS.youtube_api_key
    if not key:
        raise ConnectorError(
            "YouTube API key is not configured. Add YOUTUBE_API_KEY for reliable official comment ingestion; "
            "the zero-key path is best-effort only.",
            "CREDENTIALS_REQUIRED",
        )

    run_id = f"yt-rich-{uuid4().hex[:10]}"
    max_videos = min(request.max_videos, SETTINGS.youtube_max_videos_per_run, 10)
    max_comments = min(request.max_comments_per_video, SETTINGS.youtube_max_comments_per_video, 100)
    output: list[SocialEventIn] = []

    async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
        direct_video_id = _extract_video_id(request.query)
        search_rank: dict[str, int] = {}

        if direct_video_id:
            candidate_ids = [direct_video_id]
        else:
            candidate_count = min(25, max(8, max_videos * 5))
            search_resp = await client.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "key": key,
                    "part": "snippet",
                    "q": request.query,
                    "type": "video",
                    "order": "relevance",
                    "maxResults": candidate_count,
                    "safeSearch": "moderate",
                },
            )
            if search_resp.status_code == 429:
                raise ConnectorError("YouTube API rate limit reached.", "RATE_LIMITED")
            if search_resp.status_code == 403:
                reason = _error_reason(search_resp)
                raise ConnectorError(f"YouTube API quota/permission error{f': {reason}' if reason else ''}. Check key restriction and quota.", "RATE_LIMITED")
            if search_resp.status_code in {400, 401}:
                raise ConnectorError("YouTube API key/request is invalid.", "CREDENTIALS_REQUIRED")
            if search_resp.status_code >= 400:
                raise ConnectorError(f"YouTube search error {search_resp.status_code}: {search_resp.text[:300]}", "DEGRADED")

            candidate_ids = []
            for index, item in enumerate(search_resp.json().get("items", [])):
                video_id = str((item.get("id") or {}).get("videoId") or "")
                if video_id and video_id not in candidate_ids:
                    search_rank[video_id] = index
                    candidate_ids.append(video_id)

        details = await _video_details(client, key, candidate_ids)
        if not details:
            raise ConnectorError("YouTube returned no accessible public videos for this input.", "DEGRADED")

        details = [item for item in details if str((item.get("status") or {}).get("privacyStatus") or "public") == "public"]
        details.sort(
            key=lambda item: (
                1 if _int((item.get("statistics") or {}).get("commentCount")) > 0 else 0,
                _int((item.get("statistics") or {}).get("commentCount")),
                -search_rank.get(str(item.get("id") or ""), 0),
            ),
            reverse=True,
        )
        selected = details[: (1 if direct_video_id else max_videos)]

        for item in selected:
            video_id = str(item.get("id") or "")
            snippet = item.get("snippet") or {}
            statistics = item.get("statistics") or {}
            if not video_id:
                continue

            title = str(snippet.get("title") or "").strip()
            description = str(snippet.get("description") or "").strip()
            video_text = " — ".join(part for part in [title, description] if part).strip()
            channel_id = str(snippet.get("channelId") or "") or None
            channel_title = str(snippet.get("channelTitle") or "") or None
            thumb = _thumbnail(snippet)
            reported_comments = _int(statistics.get("commentCount"))
            root_profile: dict[str, Any] = {
                "collection_scope": "official_video_search" if not direct_video_id else "official_video_direct_url",
                "media_kind": "video",
                "thumbnail_url": thumb,
                "embed_url": f"https://www.youtube.com/embed/{video_id}",
                "video_id": video_id,
                "channel_title": channel_title,
                "reported_comment_count": reported_comments,
                "comments_state": "pending",
                "comment_selection": "relevance_with_nested_replies",
            }
            root = SocialEventIn(
                platform="youtube",
                source_event_id=f"video:{video_id}",
                event_type="video",
                author_platform_id=channel_id,
                author_display=channel_title,
                text=video_text or title or f"YouTube video {video_id}",
                created_at=_parse_dt(snippet.get("publishedAt")),
                url=f"https://www.youtube.com/watch?v={video_id}",
                conversation_id=video_id,
                engagement={
                    "views": _int(statistics.get("viewCount")),
                    "likes": _int(statistics.get("likeCount")),
                    "comments": reported_comments,
                },
                public_profile=root_profile,
                source_mode="LIVE",
                connector_run_id=run_id,
            )
            # Pydantic validates/copies mutable inputs. Rebind the working profile
            # to the model-owned dictionary so comment availability/capture state
            # written below is reflected in the event returned to callers.
            root_profile = root.public_profile
            output.append(root)

            comments_resp = await client.get(
                "https://www.googleapis.com/youtube/v3/commentThreads",
                params={
                    "key": key,
                    "part": "snippet,replies",
                    "videoId": video_id,
                    "textFormat": "plainText",
                    "maxResults": min(100, max_comments),
                    "order": "relevance",
                },
            )

            if comments_resp.status_code == 403:
                reason = _error_reason(comments_resp) or "forbidden"
                root_profile["comments_state"] = "disabled" if reason == "commentsDisabled" else "forbidden"
                root_profile["comments_note"] = reason
                continue
            if comments_resp.status_code == 429:
                root_profile["comments_state"] = "rate_limited"
                root_profile["comments_note"] = "YouTube commentThreads rate limit reached"
                continue
            if comments_resp.status_code >= 400:
                root_profile["comments_state"] = "unavailable"
                root_profile["comments_note"] = _error_reason(comments_resp) or f"HTTP {comments_resp.status_code}"
                continue

            captured = 0
            seen_comment_ids: set[str] = set()
            extra_reply_fetches = 0
            thread_items = list(comments_resp.json().get("items", []))

            for thread in thread_items:
                if captured >= max_comments:
                    break
                thread_snippet = thread.get("snippet") or {}
                top = thread_snippet.get("topLevelComment") or {}
                top_id = str(top.get("id") or thread.get("id") or "")
                top_event = _comment_event(
                    video_id=video_id,
                    raw=top,
                    root_parent=f"video:{video_id}",
                    run_id=run_id,
                    thumb=thumb,
                    is_reply=False,
                )
                if top_event and top_id not in seen_comment_ids:
                    output.append(top_event)
                    captured += 1
                    seen_comment_ids.add(top_id)

                if captured >= max_comments or not top_id:
                    continue

                inline_replies = list(((thread.get("replies") or {}).get("comments") or []))
                for reply_raw in inline_replies:
                    if captured >= max_comments:
                        break
                    reply_id = str(reply_raw.get("id") or "")
                    if not reply_id or reply_id in seen_comment_ids:
                        continue
                    reply_event = _comment_event(
                        video_id=video_id,
                        raw=reply_raw,
                        root_parent=f"comment:{top_id}",
                        run_id=run_id,
                        thumb=thumb,
                        is_reply=True,
                    )
                    if reply_event:
                        output.append(reply_event)
                        captured += 1
                        seen_comment_ids.add(reply_id)

                total_reply_count = _int(thread_snippet.get("totalReplyCount"))
                if (
                    captured < max_comments
                    and total_reply_count > len(inline_replies)
                    and extra_reply_fetches < 5
                ):
                    extra_reply_fetches += 1
                    replies_resp = await client.get(
                        "https://www.googleapis.com/youtube/v3/comments",
                        params={
                            "key": key,
                            "part": "snippet",
                            "parentId": top_id,
                            "textFormat": "plainText",
                            "maxResults": min(100, max_comments - captured),
                        },
                    )
                    if replies_resp.status_code < 400:
                        for reply_raw in replies_resp.json().get("items", []):
                            if captured >= max_comments:
                                break
                            reply_id = str(reply_raw.get("id") or "")
                            if not reply_id or reply_id in seen_comment_ids:
                                continue
                            reply_event = _comment_event(
                                video_id=video_id,
                                raw=reply_raw,
                                root_parent=f"comment:{top_id}",
                                run_id=run_id,
                                thumb=thumb,
                                is_reply=True,
                            )
                            if reply_event:
                                output.append(reply_event)
                                captured += 1
                                seen_comment_ids.add(reply_id)

            root_profile["captured_comment_count"] = captured
            root_profile["comments_state"] = "available" if captured else ("empty" if reported_comments == 0 else "no_rows_returned")
            root_profile["comments_note"] = (
                f"Captured {captured} public comments/replies through YouTube Data API v3."
                if captured
                else "No public comment rows were returned for this video in the current request."
            )

    if not output:
        raise ConnectorError("YouTube did not return any usable video/comment evidence.", "DEGRADED")
    return output
