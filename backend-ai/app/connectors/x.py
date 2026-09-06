from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from ..config import get_settings
from ..schemas import ConnectorStatus, SocialEvent, SocialEventIn
from ..services.normalizer import normalize_many

X_RECENT_SEARCH = "https://api.x.com/2/tweets/search/recent"
X_OEMBED = "https://publish.twitter.com/oembed"
TAG_RE = re.compile(r"<[^>]+>")
TWEET_ID_RE = re.compile(r"/status/(\d+)")


def status() -> ConnectorStatus:
    settings = get_settings()
    if not settings.x_bearer_token:
        return ConnectorStatus(
            platform="x",
            state="CREDENTIALS_REQUIRED",
            detail=(
                "Official X API connector is implemented but no X_BEARER_TOKEN is configured. "
                "Use REPLAY/import mode for a zero-cost demo or add official X API credits for live search."
            ),
            source_mode="LIVE",
        )
    return ConnectorStatus(
        platform="x",
        state="READY",
        detail="Official X API v2 bearer token configured; read usage is subject to the account's X API credits/limits.",
        source_mode="LIVE",
    )


def search_recent(query: str, max_results: int = 20) -> tuple[list[SocialEvent], ConnectorStatus]:
    settings = get_settings()
    current = status()
    if current.state != "READY":
        return [], current

    max_results = max(10, min(max_results, 100, settings.x_max_results_per_run))
    params = {
        "query": query,
        "max_results": max_results,
        "tweet.fields": "id,text,author_id,created_at,conversation_id,lang,public_metrics,referenced_tweets,entities",
        "expansions": "author_id",
        "user.fields": "id,name,username,description,location,public_metrics,verified",
    }
    headers = {"Authorization": f"Bearer {settings.x_bearer_token}"}
    try:
        with httpx.Client(timeout=settings.x_request_timeout_seconds) as client:
            response = client.get(X_RECENT_SEARCH, params=params, headers=headers)
    except Exception as exc:
        return [], ConnectorStatus(
            platform="x", state="ERROR", detail=f"X connector network error: {exc}", source_mode="LIVE"
        )

    if response.status_code in (402,):
        return [], ConnectorStatus(
            platform="x", state="NO_CREDITS",
            detail="X API rejected the read for insufficient credits. Replay/import remains available through the same analytics pipeline.",
            source_mode="LIVE",
        )
    if response.status_code == 429:
        return [], ConnectorStatus(
            platform="x", state="RATE_LIMITED", detail="X API rate limit reached; retry after the platform reset window.", source_mode="LIVE"
        )
    if response.status_code == 401:
        return [], ConnectorStatus(
            platform="x", state="CREDENTIALS_REQUIRED", detail="X bearer token is invalid or expired.", source_mode="LIVE"
        )
    if response.status_code == 403:
        return [], ConnectorStatus(
            platform="x", state="PERMISSION_REQUIRED",
            detail="The configured X developer project does not have permission for this read endpoint/query.", source_mode="LIVE"
        )
    if response.status_code >= 400:
        return [], ConnectorStatus(
            platform="x", state="ERROR",
            detail=f"X API HTTP {response.status_code}: {response.text[:320]}", source_mode="LIVE"
        )

    body = response.json()
    users = {
        str(user.get("id")): user
        for user in (body.get("includes", {}).get("users") or [])
    }
    inputs: list[SocialEventIn] = []
    for tweet in body.get("data") or []:
        item = _tweet_to_event(tweet, users)
        if item:
            inputs.append(item)

    events = normalize_many(inputs)
    return events, ConnectorStatus(
        platform="x", state="LIVE",
        detail=f"Official X API returned {len(events)} recent posts for the configured query.", source_mode="LIVE"
    )


def _tweet_to_event(tweet: dict[str, Any], users: dict[str, dict[str, Any]]) -> SocialEventIn | None:
    tweet_id = str(tweet.get("id") or "")
    if not tweet_id:
        return None
    author_id = str(tweet.get("author_id") or "unknown")
    user = users.get(author_id, {})
    username = user.get("username")
    references = tweet.get("referenced_tweets") or []
    parent_id = None
    event_type = "post"
    if references:
        reference = references[0]
        ref_type = str(reference.get("type") or "")
        ref_id = str(reference.get("id") or "")
        if ref_id:
            parent_id = f"x:{ref_id}"
        if ref_type == "replied_to":
            event_type = "reply"
        elif ref_type == "retweeted":
            event_type = "repost"
        elif ref_type == "quoted":
            event_type = "quote"

    created_raw = tweet.get("created_at")
    created_at = datetime.fromisoformat(str(created_raw).replace("Z", "+00:00")) if created_raw else datetime.now(timezone.utc)
    entities = tweet.get("entities") or {}
    hashtags = [tag.get("tag", "") for tag in entities.get("hashtags") or [] if tag.get("tag")]
    mentions = [mention.get("username", "") for mention in entities.get("mentions") or [] if mention.get("username")]
    urls = [entry.get("expanded_url") or entry.get("url") for entry in entities.get("urls") or [] if entry.get("expanded_url") or entry.get("url")]

    return SocialEventIn(
        platform="x",
        source_event_id=f"x:{tweet_id}",
        event_type=event_type,
        author_platform_id=author_id,
        author_display=user.get("name") or username or "X account",
        text=str(tweet.get("text") or ""),
        language=tweet.get("lang"),
        created_at=created_at,
        url=f"https://x.com/{username}/status/{tweet_id}" if username else f"https://x.com/i/web/status/{tweet_id}",
        parent_event_id=parent_id,
        conversation_id=f"x:{tweet.get('conversation_id') or tweet_id}",
        mentions=mentions,
        hashtags=hashtags,
        urls=[url for url in urls if url],
        engagement=tweet.get("public_metrics") or {},
        public_profile={
            "username": username,
            "bio": user.get("description"),
            "location": user.get("location"),
            "verified": user.get("verified"),
        },
        source_mode="LIVE",
    )


def import_public_url(url: str) -> tuple[list[SocialEvent], ConnectorStatus]:
    """Free operator-driven import for one public X post using the public oEmbed surface.

    This is deliberately labelled IMPORT, not LIVE continuous X collection. oEmbed
    does not expose the full analytical payload or a reliable creation timestamp, so
    the ingestion timestamp is recorded as a fallback and the limitation is explicit.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or parsed.netloc.lower() not in {
        "x.com", "www.x.com", "twitter.com", "www.twitter.com"
    }:
        return [], ConnectorStatus(
            platform="x", state="ERROR", detail="Only public x.com/twitter.com status URLs can be imported.", source_mode="IMPORT"
        )
    match = TWEET_ID_RE.search(parsed.path)
    if not match:
        return [], ConnectorStatus(
            platform="x", state="ERROR", detail="Could not extract a public X status ID from the URL.", source_mode="IMPORT"
        )

    try:
        with httpx.Client(timeout=12, follow_redirects=True) as client:
            response = client.get(X_OEMBED, params={"url": url, "omit_script": "true", "dnt": "true"})
        if response.status_code >= 400:
            return [], ConnectorStatus(
                platform="x", state="ERROR", detail=f"X oEmbed import returned HTTP {response.status_code}.", source_mode="IMPORT"
            )
        body = response.json()
    except Exception as exc:
        return [], ConnectorStatus(
            platform="x", state="ERROR", detail=f"X public URL import error: {exc}", source_mode="IMPORT"
        )

    rendered = str(body.get("html") or "")
    text = html.unescape(TAG_RE.sub(" ", rendered))
    text = " ".join(text.split())
    author_name = str(body.get("author_name") or "Public X account")
    tweet_id = match.group(1)
    now = datetime.now(timezone.utc)
    event = SocialEventIn(
        platform="x",
        source_event_id=f"x:{tweet_id}",
        event_type="imported_post",
        author_platform_id=author_name,
        author_display=author_name,
        text=text,
        created_at=now,
        url=url,
        conversation_id=f"x:{tweet_id}",
        public_profile={
            "timestamp_provenance": "ingest_time_fallback_oembed_does_not_supply_created_at",
            "oembed_provider": body.get("provider_name"),
        },
        source_mode="IMPORT",
    )
    return normalize_many([event]), ConnectorStatus(
        platform="x", state="READY",
        detail="Imported one public X status through oEmbed. This is limited IMPORT mode, not continuous live X search.",
        source_mode="IMPORT",
    )
