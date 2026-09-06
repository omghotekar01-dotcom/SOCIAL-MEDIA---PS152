from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

import httpx

from ..config import get_settings
from ..schemas import ConnectorStatus, SocialEvent, SocialEventIn
from ..services.normalizer import normalize_many


def status(source: Literal["instagram", "facebook"]) -> ConnectorStatus:
    settings = get_settings()
    token = settings.meta_access_token
    entity_id = settings.meta_instagram_account_id if source == "instagram" else settings.meta_facebook_page_id
    if not token:
        return ConnectorStatus(
            platform=source,
            state="CREDENTIALS_REQUIRED",
            detail=(
                "Meta access token not configured. NEXUS only uses official Graph API data for authorized "
                "Instagram professional accounts / Facebook Pages."
            ),
            source_mode="LIVE",
        )
    if not entity_id:
        return ConnectorStatus(
            platform=source,
            state="CREDENTIALS_REQUIRED",
            detail=f"Set the authorized {source} account/page ID in .env.",
            source_mode="LIVE",
        )
    return ConnectorStatus(
        platform=source,
        state="READY",
        detail=f"Official Meta Graph connector configured for an authorized {source} entity; actual fields depend on granted scopes/app review.",
        source_mode="LIVE",
    )


def sync(source: Literal["instagram", "facebook"], limit: int = 25) -> tuple[list[SocialEvent], ConnectorStatus]:
    current = status(source)
    if current.state != "READY":
        return [], current
    if source == "instagram":
        return _sync_instagram(limit)
    return _sync_facebook(limit)


def _base_url(path: str) -> str:
    settings = get_settings()
    version = settings.meta_graph_version.strip("/")
    return f"https://graph.facebook.com/{version}/{path.lstrip('/')}"


def _sync_instagram(limit: int) -> tuple[list[SocialEvent], ConnectorStatus]:
    settings = get_settings()
    account_id = settings.meta_instagram_account_id
    limit = max(1, min(limit, 100))
    inputs: list[SocialEventIn] = []
    try:
        with httpx.Client(timeout=18) as client:
            media_response = client.get(
                _base_url(f"{account_id}/media"),
                params={
                    "fields": "id,caption,timestamp,permalink,like_count,comments_count,media_type,username",
                    "limit": limit,
                    "access_token": settings.meta_access_token,
                },
            )
            if media_response.status_code >= 400:
                return [], _meta_error("instagram", media_response)
            media_items = media_response.json().get("data") or []
            for media in media_items:
                media_id = str(media.get("id") or "")
                if not media_id:
                    continue
                inputs.append(
                    SocialEventIn(
                        platform="instagram",
                        source_event_id=f"instagram:media:{media_id}",
                        event_type="post",
                        author_platform_id=str(media.get("username") or account_id),
                        author_display=str(media.get("username") or "Instagram professional account"),
                        text=str(media.get("caption") or ""),
                        created_at=_parse_time(media.get("timestamp")),
                        url=media.get("permalink"),
                        conversation_id=f"instagram:{media_id}",
                        engagement={
                            "likes": media.get("like_count"),
                            "comments": media.get("comments_count"),
                            "media_type": media.get("media_type"),
                        },
                        public_profile={"authorized_professional_account": True},
                        source_mode="LIVE",
                    )
                )
                comments_response = client.get(
                    _base_url(f"{media_id}/comments"),
                    params={
                        "fields": "id,text,timestamp,username,like_count",
                        "limit": min(50, limit),
                        "access_token": settings.meta_access_token,
                    },
                )
                if comments_response.status_code >= 400:
                    # Comment permissions may be narrower than media permissions;
                    # keep successfully authorized media instead of failing all data.
                    continue
                for comment in comments_response.json().get("data") or []:
                    comment_id = str(comment.get("id") or "")
                    if not comment_id:
                        continue
                    username = str(comment.get("username") or "Instagram commenter")
                    inputs.append(
                        SocialEventIn(
                            platform="instagram",
                            source_event_id=f"instagram:comment:{comment_id}",
                            event_type="comment",
                            author_platform_id=username,
                            author_display=username,
                            text=str(comment.get("text") or ""),
                            created_at=_parse_time(comment.get("timestamp")),
                            parent_event_id=f"instagram:media:{media_id}",
                            conversation_id=f"instagram:{media_id}",
                            engagement={"likes": comment.get("like_count")},
                            public_profile={},
                            source_mode="LIVE",
                        )
                    )
    except Exception as exc:
        return [], ConnectorStatus(
            platform="instagram", state="ERROR", detail=f"Instagram connector error: {exc}", source_mode="LIVE"
        )

    events = normalize_many(inputs)
    return events, ConnectorStatus(
        platform="instagram", state="LIVE",
        detail=f"Official Meta Graph API normalized {len(events)} authorized Instagram media/comment events.", source_mode="LIVE"
    )


def _sync_facebook(limit: int) -> tuple[list[SocialEvent], ConnectorStatus]:
    settings = get_settings()
    page_id = settings.meta_facebook_page_id
    limit = max(1, min(limit, 100))
    inputs: list[SocialEventIn] = []
    try:
        with httpx.Client(timeout=18) as client:
            response = client.get(
                _base_url(f"{page_id}/feed"),
                params={
                    "fields": "id,message,created_time,permalink_url,from,comments.limit(25){data{id,message,created_time,from}}",
                    "limit": limit,
                    "access_token": settings.meta_access_token,
                },
            )
            if response.status_code >= 400:
                return [], _meta_error("facebook", response)
            for post in response.json().get("data") or []:
                post_id = str(post.get("id") or "")
                if not post_id:
                    continue
                author = post.get("from") or {}
                inputs.append(
                    SocialEventIn(
                        platform="facebook",
                        source_event_id=f"facebook:post:{post_id}",
                        event_type="post",
                        author_platform_id=str(author.get("id") or page_id),
                        author_display=str(author.get("name") or "Authorized Facebook Page"),
                        text=str(post.get("message") or ""),
                        created_at=_parse_time(post.get("created_time")),
                        url=post.get("permalink_url"),
                        conversation_id=f"facebook:{post_id}",
                        public_profile={"authorized_page": True},
                        source_mode="LIVE",
                    )
                )
                comments = (((post.get("comments") or {}).get("data")) or [])
                for comment in comments:
                    comment_id = str(comment.get("id") or "")
                    if not comment_id:
                        continue
                    commenter = comment.get("from") or {}
                    inputs.append(
                        SocialEventIn(
                            platform="facebook",
                            source_event_id=f"facebook:comment:{comment_id}",
                            event_type="comment",
                            author_platform_id=str(commenter.get("id") or commenter.get("name") or "unknown"),
                            author_display=str(commenter.get("name") or "Facebook commenter"),
                            text=str(comment.get("message") or ""),
                            created_at=_parse_time(comment.get("created_time")),
                            parent_event_id=f"facebook:post:{post_id}",
                            conversation_id=f"facebook:{post_id}",
                            public_profile={},
                            source_mode="LIVE",
                        )
                    )
    except Exception as exc:
        return [], ConnectorStatus(
            platform="facebook", state="ERROR", detail=f"Facebook connector error: {exc}", source_mode="LIVE"
        )

    events = normalize_many(inputs)
    return events, ConnectorStatus(
        platform="facebook", state="LIVE",
        detail=f"Official Meta Graph API normalized {len(events)} authorized Facebook Page post/comment events.", source_mode="LIVE"
    )


def _meta_error(source: str, response: httpx.Response) -> ConnectorStatus:
    text = response.text[:400]
    if response.status_code in (400, 403):
        state = "PERMISSION_REQUIRED"
        detail = f"Meta Graph API denied {source} fields/scopes. Check professional/Page authorization and app permissions. {text}"
    elif response.status_code in (401,):
        state = "CREDENTIALS_REQUIRED"
        detail = f"Meta access token is invalid/expired. {text}"
    elif response.status_code == 429:
        state = "RATE_LIMITED"
        detail = "Meta Graph API rate limit reached."
    else:
        state = "ERROR"
        detail = f"Meta Graph API HTTP {response.status_code}: {text}"
    return ConnectorStatus(platform=source, state=state, detail=detail, source_mode="LIVE")


def _parse_time(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
