from __future__ import annotations

import re
from uuid import uuid4

import httpx

from .config import get_settings
from .connectors import ConnectorError, _parse_dt
from .schemas import SocialEventIn

SETTINGS = get_settings()


def _classify_meta_error(response: httpx.Response, operation: str) -> ConnectorError:
    if response.status_code == 429:
        return ConnectorError(f"Instagram {operation} rate limit reached.", "RATE_LIMITED")
    if response.status_code in {400, 401, 403}:
        detail = response.text[:400]
        return ConnectorError(
            f"Instagram {operation} is not permitted for this app/account. Check token, Instagram Public Content Access/App Review and professional-account permissions. {detail}",
            "PERMISSION_REQUIRED",
        )
    return ConnectorError(f"Instagram {operation} returned HTTP {response.status_code}: {response.text[:300]}", "DEGRADED")


async def instagram_hashtag_search(hashtag: str, limit: int = 25) -> list[SocialEventIn]:
    """Official Instagram Graph hashtag discovery for approved professional accounts."""
    token = SETTINGS.meta_access_token
    account_id = SETTINGS.meta_instagram_account_id
    if not token:
        raise ConnectorError("Meta access token is not configured.", "CREDENTIALS_REQUIRED")
    if not account_id:
        raise ConnectorError("Instagram professional account ID is not configured.", "PERMISSION_REQUIRED")

    clean = hashtag.strip().lstrip("#").strip()
    if not clean or any(ch.isspace() for ch in clean) or not re.fullmatch(r"[\w.]+", clean, flags=re.UNICODE):
        raise ConnectorError("Enter one Instagram hashtag without spaces or unsupported punctuation.", "ERROR")

    base = f"https://graph.facebook.com/{SETTINGS.meta_graph_version}"
    run_id = f"ig-hashtag-{uuid4().hex[:10]}"

    async with httpx.AsyncClient(timeout=20) as client:
        resolve = await client.get(
            f"{base}/ig_hashtag_search",
            params={"user_id": account_id, "q": clean, "access_token": token},
        )
        if resolve.status_code >= 400:
            raise _classify_meta_error(resolve, "hashtag search")
        data = resolve.json().get("data", [])
        if not data or not data[0].get("id"):
            return []
        hashtag_id = str(data[0]["id"])

        media = await client.get(
            f"{base}/{hashtag_id}/recent_media",
            params={
                "user_id": account_id,
                "access_token": token,
                "limit": min(limit, 50),
                "fields": "id,caption,comments_count,like_count,media_type,media_url,thumbnail_url,permalink,timestamp",
            },
        )
        if media.status_code >= 400:
            raise _classify_meta_error(media, "recent hashtag media")

    output: list[SocialEventIn] = []
    for item in media.json().get("data", [])[:limit]:
        media_id = str(item.get("id") or "")
        caption = str(item.get("caption") or "").strip()
        if not media_id or not caption:
            continue
        media_type = str(item.get("media_type") or "").lower()
        media_url = item.get("media_url")
        thumbnail_url = item.get("thumbnail_url") or (media_url if media_type == "image" else None)
        output.append(
            SocialEventIn(
                platform="instagram",
                source_event_id=f"hashtag:{media_id}",
                event_type="hashtag_recent_media",
                author_platform_id=None,
                author_display=None,
                text=caption,
                created_at=_parse_dt(item.get("timestamp")),
                url=item.get("permalink"),
                hashtags=[clean.lower()],
                engagement={
                    "likes": int(item.get("like_count") or 0),
                    "comments": int(item.get("comments_count") or 0),
                },
                public_profile={
                    "collection_scope": "official_public_hashtag_recent_media",
                    "queried_hashtag": clean,
                    "media_type": item.get("media_type"),
                    "media_kind": "video" if media_type in {"video", "reels"} else "image" if media_type == "image" else "carousel",
                    "media_url": media_url,
                    "thumbnail_url": thumbnail_url,
                    "author_unavailable": True,
                },
                source_mode="LIVE",
                connector_run_id=run_id,
            )
        )
    return output
