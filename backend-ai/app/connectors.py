from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx

from .config import get_settings
from .schemas import ConnectorStatus, MetaSyncRequest, SocialEventIn, XSearchRequest, YouTubeSearchRequest


SETTINGS = get_settings()
TELEGRAM_UPDATE_OFFSET = 0
TELEGRAM_POLL_LOCK = asyncio.Lock()


class ConnectorError(RuntimeError):
    def __init__(self, message: str, state: str = "ERROR"):
        super().__init__(message)
        self.state = state


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    value = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def connector_statuses() -> list[ConnectorStatus]:
    statuses = [
        ConnectorStatus(
            platform="x",
            state="READY" if SETTINGS.x_bearer_token else "CREDENTIALS_REQUIRED",
            detail=(
                "Official X API v2 connector configured. Calls are pay-per-use; hard per-run caps are enabled."
                if SETTINGS.x_bearer_token
                else "Add X_BEARER_TOKEN and X API credits for live recent-search. Replay mode remains available."
            ),
            source_mode="LIVE" if SETTINGS.x_bearer_token else None,
        ),
        ConnectorStatus(
            platform="telegram",
            state="READY" if SETTINGS.telegram_bot_token else "CREDENTIALS_REQUIRED",
            detail=(
                "Telegram Bot API live ingestion configured. Add the bot to an authorized demo group/channel."
                if SETTINGS.telegram_bot_token
                else "Add TELEGRAM_BOT_TOKEN for free live ingestion from authorized bot-visible chats."
            ),
            source_mode="LIVE" if SETTINGS.telegram_bot_token else None,
        ),
        ConnectorStatus(
            platform="youtube",
            state="READY" if SETTINGS.youtube_api_key else "CREDENTIALS_REQUIRED",
            detail=(
                "YouTube Data API v3 configured; quota-aware search/comment ingestion enabled."
                if SETTINGS.youtube_api_key
                else "Add YOUTUBE_API_KEY to enable live video/comment ingestion using Google quota."
            ),
            source_mode="LIVE" if SETTINGS.youtube_api_key else None,
        ),
        ConnectorStatus(
            platform="instagram",
            state="READY" if SETTINGS.meta_access_token and SETTINGS.meta_instagram_account_id else "PERMISSION_REQUIRED",
            detail=(
                "Authorized Instagram professional-account connector configured."
                if SETTINGS.meta_access_token and SETTINGS.meta_instagram_account_id
                else "Requires a Meta token plus an authorized Instagram professional account ID and applicable permissions."
            ),
            source_mode="LIVE" if SETTINGS.meta_access_token and SETTINGS.meta_instagram_account_id else None,
        ),
        ConnectorStatus(
            platform="facebook",
            state="READY" if SETTINGS.meta_access_token and SETTINGS.meta_facebook_page_id else "PERMISSION_REQUIRED",
            detail=(
                "Authorized Facebook Page connector configured."
                if SETTINGS.meta_access_token and SETTINGS.meta_facebook_page_id
                else "Requires a Meta token, Page ID and applicable Pages permissions/app access."
            ),
            source_mode="LIVE" if SETTINGS.meta_access_token and SETTINGS.meta_facebook_page_id else None,
        ),
        ConnectorStatus(
            platform="replay",
            state="READY",
            detail="Deterministic replay/import path is always available and is explicitly labelled REPLAY/IMPORT.",
            source_mode="REPLAY",
        ),
    ]
    return statuses


async def x_recent_search(request: XSearchRequest) -> list[SocialEventIn]:
    if not SETTINGS.x_bearer_token:
        raise ConnectorError("X bearer token is not configured.", "CREDENTIALS_REQUIRED")

    run_id = f"x-{uuid4().hex[:10]}"
    url = "https://api.x.com/2/tweets/search/recent"
    max_results = min(request.max_results, SETTINGS.x_max_results_per_run, 100)
    params: dict[str, Any] = {
        "query": request.query,
        "max_results": max(10, max_results),
        "tweet.fields": "id,text,author_id,created_at,conversation_id,public_metrics,entities,lang,referenced_tweets",
        "expansions": "author_id",
        "user.fields": "id,name,username,description,location,lang,public_metrics",
    }
    headers = {"Authorization": f"Bearer {SETTINGS.x_bearer_token}"}
    output: list[SocialEventIn] = []
    next_token: str | None = None

    async with httpx.AsyncClient(timeout=SETTINGS.x_request_timeout_seconds) as client:
        for _page in range(SETTINGS.x_max_pages_per_run):
            if next_token:
                params["next_token"] = next_token
            response = await client.get(url, params=params, headers=headers)
            if response.status_code == 429:
                raise ConnectorError("X API rate limit reached. Wait before retrying.", "RATE_LIMITED")
            if response.status_code in {402, 403}:
                raise ConnectorError(
                    "X API rejected the read request. Check pay-per-use credits, project access and app permissions.",
                    "NO_CREDITS" if response.status_code == 402 else "PERMISSION_REQUIRED",
                )
            if response.status_code == 401:
                raise ConnectorError("X API bearer token is invalid or expired.", "CREDENTIALS_REQUIRED")
            if response.status_code >= 500:
                raise ConnectorError(f"X API temporarily unavailable ({response.status_code}).", "DEGRADED")
            if response.status_code >= 400:
                detail = response.text[:400]
                raise ConnectorError(f"X API error {response.status_code}: {detail}")

            payload = response.json()
            users = {user["id"]: user for user in payload.get("includes", {}).get("users", [])}
            for tweet in payload.get("data", []):
                user = users.get(tweet.get("author_id"), {})
                entities = tweet.get("entities") or {}
                mentions = [item.get("username", "") for item in entities.get("mentions", []) if item.get("username")]
                hashtags = [item.get("tag", "").lower() for item in entities.get("hashtags", []) if item.get("tag")]
                urls = [item.get("expanded_url") or item.get("url") for item in entities.get("urls", []) if item.get("expanded_url") or item.get("url")]
                metrics = tweet.get("public_metrics") or {}
                username = user.get("username")
                permalink = f"https://x.com/{username}/status/{tweet['id']}" if username else None
                referenced = tweet.get("referenced_tweets") or []
                event_type = referenced[0].get("type", "post") if referenced else "post"
                output.append(
                    SocialEventIn(
                        platform="x",
                        source_event_id=str(tweet["id"]),
                        event_type=event_type,
                        author_platform_id=str(tweet.get("author_id") or ""),
                        author_display=username or user.get("name"),
                        text=tweet.get("text") or "",
                        language=tweet.get("lang"),
                        created_at=_parse_dt(tweet.get("created_at")),
                        url=permalink,
                        conversation_id=tweet.get("conversation_id"),
                        mentions=mentions,
                        hashtags=hashtags,
                        urls=urls,
                        engagement={
                            "likes": metrics.get("like_count", 0),
                            "reposts": metrics.get("retweet_count", 0),
                            "replies": metrics.get("reply_count", 0),
                            "quotes": metrics.get("quote_count", 0),
                        },
                        public_profile={
                            "bio": user.get("description"),
                            "region": user.get("location"),
                            "language": user.get("lang"),
                        },
                        source_mode="LIVE",
                        connector_run_id=run_id,
                    )
                )
                if len(output) >= SETTINGS.x_max_results_per_run:
                    return output
            next_token = payload.get("meta", {}).get("next_token")
            if not next_token:
                break
    return output


async def telegram_poll(max_updates: int = 50) -> list[SocialEventIn]:
    global TELEGRAM_UPDATE_OFFSET

    token = SETTINGS.telegram_bot_token
    if not token:
        raise ConnectorError("Telegram bot token is not configured.", "CREDENTIALS_REQUIRED")

    run_id = f"tg-{uuid4().hex[:10]}"
    endpoint = f"https://api.telegram.org/bot{token}/getUpdates"

    async with TELEGRAM_POLL_LOCK:
        params: dict[str, Any] = {
            "timeout": min(max(0, SETTINGS.telegram_poll_timeout_seconds), 20),
            "limit": min(max_updates, 100),
            "allowed_updates": '["message","edited_message","channel_post","edited_channel_post"]',
        }
        if TELEGRAM_UPDATE_OFFSET > 0:
            params["offset"] = TELEGRAM_UPDATE_OFFSET

        async with httpx.AsyncClient(timeout=SETTINGS.telegram_poll_timeout_seconds + 10) as client:
            response = await client.get(endpoint, params=params)

        if response.status_code == 401:
            raise ConnectorError("Telegram bot token is invalid.", "CREDENTIALS_REQUIRED")
        if response.status_code == 409:
            raise ConnectorError(
                "Telegram getUpdates conflicts with an active webhook. Remove the webhook or use a different demo bot for polling.",
                "PERMISSION_REQUIRED",
            )
        if response.status_code == 429:
            raise ConnectorError("Telegram Bot API rate-limited the request.", "RATE_LIMITED")
        if response.status_code >= 400:
            raise ConnectorError(f"Telegram API error {response.status_code}: {response.text[:300]}")
        body = response.json()
        if not body.get("ok"):
            raise ConnectorError(f"Telegram API returned an error: {body.get('description', 'unknown error')}")

        updates = body.get("result", [])
        if updates:
            update_ids = [int(item.get("update_id")) for item in updates if item.get("update_id") is not None]
            if update_ids:
                TELEGRAM_UPDATE_OFFSET = max(TELEGRAM_UPDATE_OFFSET, max(update_ids) + 1)

    allowed = SETTINGS.telegram_allowed_chat_id_set
    output: list[SocialEventIn] = []
    for update in updates:
        container = None
        event_type = "message"
        for key in ("message", "edited_message", "channel_post", "edited_channel_post"):
            if key in update:
                container = update[key]
                event_type = key
                break
        if not container:
            continue
        chat = container.get("chat") or {}
        chat_id = chat.get("id")
        if allowed and chat_id not in allowed:
            continue
        text = container.get("text") or container.get("caption") or ""
        if not text.strip():
            continue
        sender = container.get("from") or container.get("sender_chat") or {}
        sender_id = sender.get("id") or chat_id
        display = sender.get("username") or sender.get("title") or " ".join(
            part for part in [sender.get("first_name"), sender.get("last_name")] if part
        ) or chat.get("username") or chat.get("title")
        username = chat.get("username")
        message_id = container.get("message_id")
        permalink = f"https://t.me/{username}/{message_id}" if username and message_id else None
        reply = container.get("reply_to_message") or {}
        output.append(
            SocialEventIn(
                platform="telegram",
                source_event_id=f"{chat_id}:{message_id}",
                event_type=event_type,
                author_platform_id=str(sender_id) if sender_id is not None else None,
                author_display=display,
                text=text,
                created_at=datetime.fromtimestamp(container.get("date", 0), tz=timezone.utc),
                url=permalink,
                parent_event_id=(f"{chat_id}:{reply.get('message_id')}" if reply.get("message_id") else None),
                conversation_id=str(chat_id),
                engagement={},
                public_profile={"language": container.get("from", {}).get("language_code")},
                source_mode="LIVE",
                connector_run_id=run_id,
            )
        )
    return output


async def youtube_search(request: YouTubeSearchRequest) -> list[SocialEventIn]:
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
        if search_resp.status_code == 403:
            raise ConnectorError("YouTube API quota/permission error. Check key and quota.", "RATE_LIMITED")
        if search_resp.status_code >= 400:
            raise ConnectorError(f"YouTube search error {search_resp.status_code}: {search_resp.text[:300]}")

        for item in search_resp.json().get("items", []):
            video_id = item.get("id", {}).get("videoId")
            if not video_id:
                continue
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
            if comments_resp.status_code == 403:
                # Comments can be disabled for a video; skip instead of failing the run.
                continue
            if comments_resp.status_code >= 400:
                continue
            for thread in comments_resp.json().get("items", []):
                top = thread.get("snippet", {}).get("topLevelComment", {})
                snippet = top.get("snippet", {})
                comment_id = top.get("id") or thread.get("id")
                if not comment_id:
                    continue
                output.append(
                    SocialEventIn(
                        platform="youtube",
                        source_event_id=str(comment_id),
                        event_type="video_comment",
                        author_platform_id=snippet.get("authorChannelId", {}).get("value"),
                        author_display=snippet.get("authorDisplayName"),
                        text=snippet.get("textDisplay") or snippet.get("textOriginal") or "",
                        created_at=_parse_dt(snippet.get("publishedAt")),
                        url=f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}",
                        conversation_id=video_id,
                        engagement={"likes": snippet.get("likeCount", 0)},
                        public_profile={},
                        source_mode="LIVE",
                        connector_run_id=run_id,
                    )
                )
    return output


async def meta_sync(request: MetaSyncRequest) -> list[SocialEventIn]:
    token = SETTINGS.meta_access_token
    if not token:
        raise ConnectorError("Meta access token is not configured.", "CREDENTIALS_REQUIRED")

    run_id = f"meta-{uuid4().hex[:10]}"
    base = f"https://graph.facebook.com/{SETTINGS.meta_graph_version}"
    output: list[SocialEventIn] = []

    if request.source == "instagram":
        account_id = SETTINGS.meta_instagram_account_id
        if not account_id:
            raise ConnectorError("Instagram professional account ID is not configured.", "PERMISSION_REQUIRED")
        url = f"{base}/{account_id}/media"
        params = {
            "access_token": token,
            "limit": request.limit,
            "fields": "id,caption,timestamp,permalink,username,comments.limit(25){id,text,timestamp,username}",
        }
    else:
        page_id = SETTINGS.meta_facebook_page_id
        if not page_id:
            raise ConnectorError("Facebook Page ID is not configured.", "PERMISSION_REQUIRED")
        url = f"{base}/{page_id}/feed"
        params = {
            "access_token": token,
            "limit": request.limit,
            "fields": "id,message,created_time,permalink_url,from,comments.limit(25){id,message,created_time,from}",
        }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, params=params)
    if response.status_code in {400, 401, 403}:
        raise ConnectorError(
            f"Meta permission/token error ({response.status_code}). Check professional/Page access and app permissions.",
            "PERMISSION_REQUIRED",
        )
    if response.status_code == 429:
        raise ConnectorError("Meta API rate limit reached.", "RATE_LIMITED")
    if response.status_code >= 400:
        raise ConnectorError(f"Meta API error {response.status_code}: {response.text[:300]}")

    payload = response.json()
    for item in payload.get("data", []):
        if request.source == "instagram":
            post_text = item.get("caption") or ""
            username = item.get("username")
            if post_text:
                output.append(
                    SocialEventIn(
                        platform="instagram",
                        source_event_id=str(item["id"]),
                        event_type="post",
                        author_platform_id=SETTINGS.meta_instagram_account_id,
                        author_display=username,
                        text=post_text,
                        created_at=_parse_dt(item.get("timestamp")),
                        url=item.get("permalink"),
                        engagement={},
                        public_profile={},
                        source_mode="LIVE",
                        connector_run_id=run_id,
                    )
                )
            for comment in (item.get("comments") or {}).get("data", []):
                output.append(
                    SocialEventIn(
                        platform="instagram",
                        source_event_id=str(comment["id"]),
                        event_type="comment",
                        author_display=comment.get("username"),
                        text=comment.get("text") or "",
                        created_at=_parse_dt(comment.get("timestamp")),
                        parent_event_id=str(item["id"]),
                        conversation_id=str(item["id"]),
                        source_mode="LIVE",
                        connector_run_id=run_id,
                    )
                )
        else:
            author = item.get("from") or {}
            post_text = item.get("message") or ""
            if post_text:
                output.append(
                    SocialEventIn(
                        platform="facebook",
                        source_event_id=str(item["id"]),
                        event_type="post",
                        author_platform_id=author.get("id"),
                        author_display=author.get("name"),
                        text=post_text,
                        created_at=_parse_dt(item.get("created_time")),
                        url=item.get("permalink_url"),
                        source_mode="LIVE",
                        connector_run_id=run_id,
                    )
                )
            for comment in (item.get("comments") or {}).get("data", []):
                c_author = comment.get("from") or {}
                output.append(
                    SocialEventIn(
                        platform="facebook",
                        source_event_id=str(comment["id"]),
                        event_type="comment",
                        author_platform_id=c_author.get("id"),
                        author_display=c_author.get("name"),
                        text=comment.get("message") or "",
                        created_at=_parse_dt(comment.get("created_time")),
                        parent_event_id=str(item["id"]),
                        conversation_id=str(item["id"]),
                        source_mode="LIVE",
                        connector_run_id=run_id,
                    )
                )
    await asyncio.sleep(0)
    return output
