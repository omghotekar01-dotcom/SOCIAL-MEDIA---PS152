from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx

from .config import get_settings
from .connectors import ConnectorError
from .free_connectors import (
    USER_AGENT,
    _configured_bridge,
    _extract_text_entities,
    _safe_int,
    instagram_public_profile as _base_instagram_public_profile,
    mastodon_search as _base_mastodon_search,
    reddit_public_search as _base_reddit_public_search,
)
from .schemas import SocialEventIn

SETTINGS = get_settings()


def _reddit_events(payload: dict[str, Any], limit: int, collection_scope: str) -> list[SocialEventIn]:
    output: list[SocialEventIn] = []
    run_id = f"reddit-{collection_scope}-{uuid4().hex[:10]}"
    children = payload.get("data", {}).get("children", [])
    for child in children[:limit]:
        data = child.get("data") or {}
        post_id = str(data.get("id") or "")
        title = str(data.get("title") or "")
        body = str(data.get("selftext") or "")
        text = " — ".join(part for part in [title, body] if part).strip()
        if not post_id or not text:
            continue
        permalink = str(data.get("permalink") or "")
        url = f"https://www.reddit.com{permalink}" if permalink.startswith("/") else str(data.get("url") or "")
        hashtags, mentions, urls = _extract_text_entities(text)
        created = float(data.get("created_utc") or 0)
        output.append(
            SocialEventIn(
                platform="reddit",
                source_event_id=post_id,
                event_type="submission",
                author_platform_id=str(data.get("author_fullname") or data.get("author") or "unknown"),
                author_display=str(data.get("author") or "unknown"),
                text=text,
                created_at=datetime.fromtimestamp(created, tz=timezone.utc) if created else datetime.now(timezone.utc),
                url=url or None,
                conversation_id=str(data.get("subreddit") or ""),
                mentions=mentions,
                hashtags=hashtags,
                urls=urls,
                engagement={
                    "score": _safe_int(data.get("score")),
                    "comments": _safe_int(data.get("num_comments")),
                    "upvote_ratio": data.get("upvote_ratio"),
                },
                public_profile={"subreddit": data.get("subreddit"), "collection_scope": collection_scope},
                source_mode="LIVE",
                connector_run_id=run_id,
            )
        )
    return output


async def _reddit_oauth_search(query: str, limit: int) -> list[SocialEventIn]:
    if not SETTINGS.reddit_client_id or not SETTINGS.reddit_client_secret:
        raise ConnectorError("Reddit OAuth credentials are not configured.", "CREDENTIALS_REQUIRED")

    headers = {"User-Agent": SETTINGS.reddit_user_agent or USER_AGENT}
    try:
        async with httpx.AsyncClient(timeout=SETTINGS.public_http_timeout_seconds, follow_redirects=True, headers=headers) as client:
            token_response = await client.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=(SETTINGS.reddit_client_id, SETTINGS.reddit_client_secret),
                data={"grant_type": "client_credentials"},
            )
            if token_response.status_code in {401, 403}:
                raise ConnectorError("Reddit OAuth credentials were rejected.", "CREDENTIALS_REQUIRED")
            if token_response.status_code == 429:
                raise ConnectorError("Reddit OAuth token endpoint rate-limited this request.", "RATE_LIMITED")
            if token_response.status_code >= 400:
                raise ConnectorError(f"Reddit OAuth token endpoint returned HTTP {token_response.status_code}.", "DEGRADED")
            token = str(token_response.json().get("access_token") or "")
            if not token:
                raise ConnectorError("Reddit OAuth did not return an access token.", "CREDENTIALS_REQUIRED")

            response = await client.get(
                "https://oauth.reddit.com/search",
                params={"q": query, "limit": min(limit, 100), "sort": "new", "raw_json": 1},
                headers={**headers, "Authorization": f"bearer {token}"},
            )
    except ConnectorError:
        raise
    except httpx.HTTPError as exc:
        raise ConnectorError(f"Reddit OAuth search could not be reached: {exc}", "DEGRADED") from exc

    if response.status_code == 429:
        raise ConnectorError("Reddit OAuth search rate-limited this request.", "RATE_LIMITED")
    if response.status_code in {401, 403}:
        raise ConnectorError("Reddit OAuth search permission was rejected.", "PERMISSION_REQUIRED")
    if response.status_code >= 400:
        raise ConnectorError(f"Reddit OAuth search returned HTTP {response.status_code}.", "DEGRADED")
    return _reddit_events(response.json(), limit, "oauth_search")


async def reddit_resilient_search(query: str, limit: int = 25) -> list[SocialEventIn]:
    """Prefer OAuth when configured, otherwise use the low-volume public path.

    A failed OAuth attempt is allowed to fall back to public JSON because some
    networks block one Reddit hostname but not the other. The final error keeps
    both failure reasons instead of pretending the connector succeeded.
    """
    errors: list[str] = []
    if SETTINGS.reddit_client_id and SETTINGS.reddit_client_secret:
        try:
            events = await _reddit_oauth_search(query, limit)
            if events:
                return events
        except ConnectorError as exc:
            errors.append(f"OAuth: {exc}")
    try:
        events = await _base_reddit_public_search(query, limit)
        if events:
            return events
        errors.append("public JSON returned no results")
    except ConnectorError as exc:
        errors.append(f"public JSON: {exc}")
        state = exc.state
    else:
        state = "DEGRADED"
    raise ConnectorError("Reddit sources unavailable for this run — " + " | ".join(errors), state)


def _mastodon_candidates(requested: str | None) -> list[str]:
    candidates: list[str] = []
    for raw in [requested or "", SETTINGS.mastodon_base_url, *SETTINGS.mastodon_fallback_base_url_list]:
        clean = raw.strip().rstrip("/")
        if clean and clean not in candidates:
            candidates.append(clean)
    return candidates[:5]


async def mastodon_resilient_search(query: str, limit: int = 25, base_url: str | None = None) -> list[SocialEventIn]:
    errors: list[str] = []
    last_state = "DEGRADED"
    for candidate in _mastodon_candidates(base_url):
        try:
            events = await _base_mastodon_search(query, limit, candidate)
            if events:
                for event in events:
                    profile = dict(event.public_profile or {})
                    profile["resilient_instance_selection"] = candidate
                    event.public_profile = profile
                return events
            errors.append(f"{candidate}: no statuses")
        except ConnectorError as exc:
            last_state = exc.state
            errors.append(f"{candidate}: {exc}")
    raise ConnectorError("No configured Mastodon instance returned searchable public statuses — " + " | ".join(errors[:5]), last_state)


async def instagram_resilient_profile(profile: str, limit: int = 20) -> list[SocialEventIn]:
    """Use an explicitly configured permitted public bridge before Instaloader.

    This never bypasses login/private controls. Without a bridge it preserves the
    existing public-profile collector and surfaces provider restrictions honestly.
    """
    bridge_error: ConnectorError | None = None
    if SETTINGS.instagram_public_rss_url_template.strip():
        try:
            events = await _configured_bridge("instagram", SETTINGS.instagram_public_rss_url_template, profile, profile, limit)
            if events:
                return events
        except ConnectorError as exc:
            bridge_error = exc
    try:
        return await _base_instagram_public_profile(profile, limit)
    except ConnectorError as exc:
        if bridge_error:
            raise ConnectorError(f"Instagram public paths unavailable — bridge: {bridge_error} | profile fallback: {exc}", exc.state) from exc
        raise
