from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from ..config import get_settings
from ..schemas import ConnectorStatus, SocialEvent, SocialEventIn
from ..services.normalizer import normalize_many

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
SEARCH_URL = "https://oauth.reddit.com/search"


def status() -> ConnectorStatus:
    settings = get_settings()
    if not settings.reddit_enabled:
        return ConnectorStatus(
            platform="reddit",
            state="DISABLED",
            detail="Reddit connector is optional and disabled by default. Enable only for an eligible/authorized Data API use case.",
            source_mode="LIVE",
        )
    if not settings.reddit_client_id or not settings.reddit_client_secret:
        return ConnectorStatus(
            platform="reddit",
            state="CREDENTIALS_REQUIRED",
            detail="Set Reddit OAuth client credentials after confirming the project's Data API eligibility/policy requirements.",
            source_mode="LIVE",
        )
    return ConnectorStatus(
        platform="reddit",
        state="READY",
        detail="Reddit OAuth connector configured. NEXUS respects API limits and ignores deleted/removed text.",
        source_mode="LIVE",
    )


def search(query: str, limit: int = 20, include_comments: bool = True) -> tuple[list[SocialEvent], ConnectorStatus]:
    settings = get_settings()
    current = status()
    if current.state != "READY":
        return [], current

    try:
        with httpx.Client(timeout=18) as client:
            token_response = client.post(
                TOKEN_URL,
                data={"grant_type": "client_credentials"},
                auth=(settings.reddit_client_id, settings.reddit_client_secret),
                headers={"User-Agent": settings.reddit_user_agent},
            )
            if token_response.status_code >= 400:
                return [], ConnectorStatus(
                    platform="reddit", state="CREDENTIALS_REQUIRED",
                    detail=f"Reddit OAuth token request failed with HTTP {token_response.status_code}.", source_mode="LIVE"
                )
            token = token_response.json().get("access_token")
            if not token:
                return [], ConnectorStatus(platform="reddit", state="ERROR", detail="Reddit OAuth response had no access token.", source_mode="LIVE")
            headers = {"Authorization": f"bearer {token}", "User-Agent": settings.reddit_user_agent}
            response = client.get(
                SEARCH_URL,
                params={"q": query, "sort": "new", "limit": max(1, min(limit, 50)), "type": "link", "raw_json": 1},
                headers=headers,
            )
            if response.status_code == 429:
                return [], ConnectorStatus(platform="reddit", state="RATE_LIMITED", detail="Reddit Data API rate limit reached.", source_mode="LIVE")
            if response.status_code in (401, 403):
                return [], ConnectorStatus(platform="reddit", state="PERMISSION_REQUIRED", detail="Reddit Data API access was denied for this app/use case.", source_mode="LIVE")
            response.raise_for_status()

            inputs: list[SocialEventIn] = []
            posts = (((response.json().get("data") or {}).get("children")) or [])
            for wrapper in posts:
                post = wrapper.get("data") or {}
                post_event = _post_to_event(post)
                if post_event:
                    inputs.append(post_event)
                if include_comments and post.get("id"):
                    inputs.extend(_fetch_comments(client, headers, str(post["id"]), str(post.get("permalink") or ""), max_comments=15))
    except httpx.HTTPStatusError as exc:
        return [], ConnectorStatus(
            platform="reddit", state="ERROR",
            detail=f"Reddit Data API HTTP {exc.response.status_code}: {exc.response.text[:260]}", source_mode="LIVE"
        )
    except Exception as exc:
        return [], ConnectorStatus(platform="reddit", state="ERROR", detail=f"Reddit connector error: {exc}", source_mode="LIVE")

    events = normalize_many(inputs)
    return events, ConnectorStatus(
        platform="reddit", state="LIVE", detail=f"Reddit Data API normalized {len(events)} eligible public posts/comments.", source_mode="LIVE"
    )


def _post_to_event(post: dict[str, Any]) -> SocialEventIn | None:
    post_id = str(post.get("id") or "")
    author = str(post.get("author") or "")
    if not post_id or not author or author in ("[deleted]", "[removed]"):
        return None
    title = str(post.get("title") or "")
    body = str(post.get("selftext") or "")
    if body in ("[deleted]", "[removed]"):
        body = ""
    subreddit = str(post.get("subreddit") or "")
    permalink = str(post.get("permalink") or "")
    return SocialEventIn(
        platform="reddit",
        source_event_id=f"reddit:post:{post_id}",
        event_type="post",
        author_platform_id=author,
        author_display=author,
        text=f"{title}. {body}".strip(),
        created_at=datetime.fromtimestamp(float(post.get("created_utc") or 0), tz=timezone.utc),
        url=f"https://www.reddit.com{permalink}" if permalink else None,
        conversation_id=f"reddit:{post_id}",
        engagement={"score": post.get("score"), "comments": post.get("num_comments")},
        public_profile={"subreddit": subreddit},
        source_mode="LIVE",
    )


def _fetch_comments(
    client: httpx.Client,
    headers: dict[str, str],
    post_id: str,
    permalink: str,
    max_comments: int,
) -> list[SocialEventIn]:
    response = client.get(
        f"https://oauth.reddit.com/comments/{post_id}",
        params={"limit": max_comments, "sort": "new", "depth": 1, "raw_json": 1},
        headers=headers,
    )
    if response.status_code >= 400:
        return []
    body = response.json()
    if not isinstance(body, list) or len(body) < 2:
        return []
    listing = ((body[1].get("data") or {}).get("children") or [])
    result: list[SocialEventIn] = []
    for wrapper in listing[:max_comments]:
        comment = wrapper.get("data") or {}
        comment_id = str(comment.get("id") or "")
        author = str(comment.get("author") or "")
        text = str(comment.get("body") or "")
        if not comment_id or not author or author in ("[deleted]", "[removed]") or text in ("[deleted]", "[removed]"):
            continue
        result.append(
            SocialEventIn(
                platform="reddit",
                source_event_id=f"reddit:comment:{comment_id}",
                event_type="comment",
                author_platform_id=author,
                author_display=author,
                text=text,
                created_at=datetime.fromtimestamp(float(comment.get("created_utc") or 0), tz=timezone.utc),
                url=f"https://www.reddit.com{comment.get('permalink')}" if comment.get("permalink") else (f"https://www.reddit.com{permalink}" if permalink else None),
                parent_event_id=f"reddit:post:{post_id}",
                conversation_id=f"reddit:{post_id}",
                engagement={"score": comment.get("score")},
                public_profile={"subreddit": comment.get("subreddit")},
                source_mode="LIVE",
            )
        )
    return result
