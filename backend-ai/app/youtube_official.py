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
        raise ConnectorError(
            f"YouTube API quota/permission error while reading videos{f': {reason}' if reason else ''}.",
            "RATE_LIMITED",
        )
    if response.status_code in {400, 401}:
        raise ConnectorError("YouTube API key/request is invalid.", "CREDENTIALS_REQUIRED")
    if response.status_code >= 400:
        raise ConnectorError(f"YouTube videos.list error {response.status_code}: {response.text[:300]}", "DEGRADED")
    return list(response.json().get("items", []))


def _within_count_cap(captured: int, requested_cap: int) -> bool:
    # 0 means exhaustive/provider-bounded mode: no application-side count cap.
    return requested_cap <= 0 or captured < requested_cap


def _page_size(captured: int, requested_cap: int) -> int:
    if requested_cap <= 0:
        return 100
    return max(1, min(100, requested_cap - captured))


def _within_page_cap(page_number: int, configured_cap: int) -> bool:
    # 0 means no application-side page ceiling. Provider quota/rate limits and
    # nextPageToken are then the natural boundaries.
    return configured_cap <= 0 or page_number < configured_cap


async def youtube_official_search(request: YouTubeSearchRequest) -> list[SocialEventIn]:
    """Official YouTube Data API v3 video + exhaustive comment/reply ingestion.

    ``max_comments_per_video=0`` explicitly requests provider-bounded exhaustive
    collection and therefore overrides stale positive count caps in an old local
    .env. Positive request values can still be constrained by an operator cap.
    """
    key = SETTINGS.youtube_api_key
    if not key:
        raise ConnectorError(
            "YouTube API key is not configured. Add YOUTUBE_API_KEY for reliable official comment ingestion; "
            "the zero-key path is metadata-only/best-effort.",
            "CREDENTIALS_REQUIRED",
        )

    run_id = f"yt-rich-{uuid4().hex[:10]}"
    max_videos = min(request.max_videos, SETTINGS.youtube_max_videos_per_run, 10)
    requested_comment_cap = int(request.max_comments_per_video)
    configured_comment_cap = int(SETTINGS.youtube_max_comments_per_video)
    # Explicit 0 means exhaustive and wins over a stale YOUTUBE_MAX_COMMENTS_PER_VIDEO
    # value left from older project versions. Positive requests remain cap-aware.
    if requested_comment_cap > 0 and configured_comment_cap > 0:
        requested_comment_cap = min(requested_comment_cap, configured_comment_cap)

    output: list[SocialEventIn] = []

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
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
                raise ConnectorError(
                    f"YouTube API quota/permission error{f': {reason}' if reason else ''}. Check key restriction and quota.",
                    "RATE_LIMITED",
                )
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

        details = [
            item
            for item in details
            if str((item.get("status") or {}).get("privacyStatus") or "public") == "public"
        ]
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
                "comment_selection": "provider_exhaustive_pagination",
                "requested_comment_cap": requested_comment_cap,
                "exhaustive_requested": requested_comment_cap <= 0,
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
            root_profile = root.public_profile
            output.append(root)

            captured = 0
            top_level_captured = 0
            replies_captured = 0
            seen_comment_ids: set[str] = set()
            thread_pages = 0
            reply_pages = 0
            thread_page_token: str | None = None
            collection_complete = True
            stop_reason = "provider_exhausted"
            first_thread_request = True

            while _within_count_cap(captured, requested_comment_cap) and _within_page_cap(
                thread_pages, SETTINGS.youtube_max_comment_pages_per_video
            ):
                params: dict[str, Any] = {
                    "key": key,
                    "part": "snippet,replies",
                    "videoId": video_id,
                    "textFormat": "plainText",
                    "maxResults": _page_size(captured, requested_comment_cap),
                    "order": "time",
                }
                if thread_page_token:
                    params["pageToken"] = thread_page_token

                comments_resp = await client.get(
                    "https://www.googleapis.com/youtube/v3/commentThreads",
                    params=params,
                )
                thread_pages += 1

                if comments_resp.status_code == 403:
                    reason = _error_reason(comments_resp) or "forbidden"
                    if first_thread_request and reason == "commentsDisabled":
                        root_profile["comments_state"] = "disabled"
                        root_profile["comments_note"] = reason
                        stop_reason = "comments_disabled"
                    else:
                        collection_complete = False
                        stop_reason = reason or "forbidden"
                    break
                if comments_resp.status_code == 429:
                    collection_complete = False
                    stop_reason = "rate_limited"
                    break
                if comments_resp.status_code >= 400:
                    collection_complete = False
                    stop_reason = _error_reason(comments_resp) or f"HTTP {comments_resp.status_code}"
                    break

                first_thread_request = False
                payload = comments_resp.json()
                thread_items = list(payload.get("items", []))

                for thread in thread_items:
                    if not _within_count_cap(captured, requested_comment_cap):
                        collection_complete = False
                        stop_reason = "requested_count_cap"
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
                        top_level_captured += 1
                        seen_comment_ids.add(top_id)

                    if not top_id or not _within_count_cap(captured, requested_comment_cap):
                        continue

                    inline_replies = list(((thread.get("replies") or {}).get("comments") or []))
                    for reply_raw in inline_replies:
                        if not _within_count_cap(captured, requested_comment_cap):
                            collection_complete = False
                            stop_reason = "requested_count_cap"
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
                            replies_captured += 1
                            seen_comment_ids.add(reply_id)

                    total_reply_count = _int(thread_snippet.get("totalReplyCount"))
                    if total_reply_count <= len(inline_replies) or not _within_count_cap(captured, requested_comment_cap):
                        continue

                    reply_page_token: str | None = None
                    per_thread_reply_page = 0
                    while _within_count_cap(captured, requested_comment_cap) and _within_page_cap(
                        per_thread_reply_page, SETTINGS.youtube_max_reply_pages_per_thread
                    ):
                        reply_params: dict[str, Any] = {
                            "key": key,
                            "part": "snippet",
                            "parentId": top_id,
                            "textFormat": "plainText",
                            "maxResults": _page_size(captured, requested_comment_cap),
                        }
                        if reply_page_token:
                            reply_params["pageToken"] = reply_page_token
                        replies_resp = await client.get(
                            "https://www.googleapis.com/youtube/v3/comments",
                            params=reply_params,
                        )
                        reply_pages += 1
                        per_thread_reply_page += 1

                        if replies_resp.status_code == 429:
                            collection_complete = False
                            stop_reason = "rate_limited_while_fetching_replies"
                            break
                        if replies_resp.status_code >= 400:
                            collection_complete = False
                            stop_reason = _error_reason(replies_resp) or f"reply_http_{replies_resp.status_code}"
                            break

                        reply_payload = replies_resp.json()
                        for reply_raw in reply_payload.get("items", []):
                            if not _within_count_cap(captured, requested_comment_cap):
                                collection_complete = False
                                stop_reason = "requested_count_cap"
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
                                replies_captured += 1
                                seen_comment_ids.add(reply_id)

                        reply_page_token = reply_payload.get("nextPageToken")
                        if not reply_page_token:
                            break

                    if (
                        SETTINGS.youtube_max_reply_pages_per_thread > 0
                        and per_thread_reply_page >= SETTINGS.youtube_max_reply_pages_per_thread
                        and reply_page_token
                    ):
                        collection_complete = False
                        stop_reason = "reply_page_ceiling"

                thread_page_token = payload.get("nextPageToken")
                if not thread_page_token:
                    break

            if (
                SETTINGS.youtube_max_comment_pages_per_video > 0
                and thread_pages >= SETTINGS.youtube_max_comment_pages_per_video
                and thread_page_token
            ):
                collection_complete = False
                stop_reason = "comment_thread_page_ceiling"

            root_profile["captured_comment_count"] = captured
            root_profile["captured_top_level_comment_count"] = top_level_captured
            root_profile["captured_reply_count"] = replies_captured
            root_profile["comment_thread_pages_fetched"] = thread_pages
            root_profile["reply_pages_fetched"] = reply_pages
            root_profile["collection_complete"] = collection_complete
            root_profile["collection_stop_reason"] = stop_reason
            root_profile["coverage_ratio"] = (
                round(min(1.0, captured / reported_comments), 4)
                if reported_comments > 0
                else (1.0 if captured == 0 else None)
            )

            if root_profile.get("comments_state") == "disabled":
                continue
            if captured:
                root_profile["comments_state"] = "available"
                completeness = "complete/provider-exhausted" if collection_complete else f"partial ({stop_reason})"
                root_profile["comments_note"] = (
                    f"Captured {captured} public comments/replies across {thread_pages} comment-thread page(s) "
                    f"and {reply_pages} reply page(s); collection {completeness}."
                )
            elif reported_comments == 0:
                root_profile["comments_state"] = "empty"
                root_profile["comments_note"] = "YouTube reports no public comments for this video."
            else:
                root_profile["comments_state"] = "no_rows_returned"
                root_profile["comments_note"] = f"YouTube reports comments, but no public rows were returned ({stop_reason})."

    if not output:
        raise ConnectorError("YouTube did not return any usable video/comment evidence.", "DEGRADED")
    return output
