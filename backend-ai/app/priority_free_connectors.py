from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote, urlparse
from uuid import uuid4

import httpx
from bs4 import BeautifulSoup

from .connectors import ConnectorError
from .free_connectors import (
    _extract_text_entities,
    _stable_id,
    telegram_public_channel as _telegram_public_channel_original,
    x_public_bridge as _x_public_bridge_original,
)
from .schemas import SocialEventIn

_X_URL_RE = re.compile(r"https?://(?:www\.)?(?:x\.com|twitter\.com)/[A-Za-z0-9_]+/status/\d+(?:\?[^\s,]*)?", re.I)


def _query_terms(query: str) -> list[str]:
    quoted = [item.strip().lower() for item in re.findall(r'"([^"]{2,100})"', query)]
    cleaned = re.sub(r'"[^"]+"', " ", query)
    raw = re.findall(r"[#@]?[\w.-]{2,80}", cleaned, flags=re.UNICODE)
    stop = {"and", "or", "the", "this", "that", "with", "from", "into", "about", "is", "are", "of", "in", "on", "for", "to", "a", "an"}
    terms = quoted + [term.lower() for term in raw if term.lower().lstrip("#@") not in stop]
    seen: set[str] = set()
    return [term for term in terms if not (term in seen or seen.add(term))]


def _matches_query(event: SocialEventIn, query: str) -> bool:
    terms = _query_terms(query)
    if not terms:
        return True
    haystack = " ".join(
        [
            event.text or "",
            " ".join(f"#{tag}" for tag in event.hashtags),
            " ".join(f"@{mention}" for mention in event.mentions),
        ]
    ).lower()
    # A monitored-source search should be useful for natural-language queries,
    # so any meaningful query token/phrase is enough to include the post.
    return any(term in haystack for term in terms)


def _parse_channel_spec(spec: str) -> tuple[list[str], str]:
    # WorkspaceSearchRequest encodes an optional query after `||` so we can keep
    # the existing public connector signature while supporting multi-channel search.
    channel_part, sep, query = spec.partition("||")
    channels: list[str] = []
    for raw in re.split(r"[,;\s]+", channel_part):
        clean = raw.strip().lstrip("@").strip("/")
        if clean and re.fullmatch(r"[A-Za-z0-9_]{4,64}", clean) and clean not in channels:
            channels.append(clean)
    return channels[:12], query.strip() if sep else ""


async def telegram_monitored_search(channel_spec: str, limit: int = 25) -> list[SocialEventIn]:
    """Search latest posts across configured public Telegram channels at zero cost.

    Telegram's public preview endpoint is channel-scoped, not a global search API.
    NEXUS therefore monitors a deliberate allow-list of public channels, collects
    their latest posts, and locally filters them against the active analyst query.
    This is deterministic, free, and avoids pretending we have unrestricted global
    Telegram search access.
    """
    channels, query = _parse_channel_spec(channel_spec)
    if not channels:
        raise ConnectorError("Configure at least one public Telegram channel username.", "ERROR")

    per_channel = max(12, min(40, limit * 2))
    results = await asyncio.gather(
        *(_telegram_public_channel_original(channel, per_channel) for channel in channels),
        return_exceptions=True,
    )

    output: list[SocialEventIn] = []
    failures: list[str] = []
    for channel, result in zip(channels, results):
        if isinstance(result, Exception):
            failures.append(f"{channel}: {str(result)[:120]}")
            continue
        for event in result:
            if query and not _matches_query(event, query):
                continue
            profile = dict(event.public_profile or {})
            profile.update(
                {
                    "monitored_channel": channel,
                    "workspace_query_filter": query or None,
                    "collection_scope": "public_preview_monitored_channel",
                }
            )
            output.append(event.model_copy(update={"public_profile": profile}))

    # Deduplicate and rank newest first; one public post should appear only once.
    dedup: dict[str, SocialEventIn] = {}
    for event in output:
        dedup[f"{event.platform}:{event.source_event_id}"] = event
    ranked = sorted(dedup.values(), key=lambda event: event.created_at, reverse=True)[:limit]
    if not ranked and failures and len(failures) == len(channels):
        raise ConnectorError("All configured Telegram channels were unavailable: " + " | ".join(failures[:3]), "DEGRADED")
    return ranked


def _extract_x_urls(value: str) -> list[str]:
    urls: list[str] = []
    for match in _X_URL_RE.finditer(value or ""):
        url = match.group(0).rstrip(".,;:!?)\"]}")
        if url not in urls:
            urls.append(url)
    return urls[:50]


def _x_status_id(url: str) -> str:
    match = re.search(r"/status/(\d+)", url)
    return match.group(1) if match else _stable_id(url)


def _parse_x_date(blockquote: BeautifulSoup) -> datetime:
    anchors = blockquote.find_all("a")
    for anchor in reversed(anchors):
        raw = anchor.get_text(" ", strip=True)
        for fmt in ("%b %d, %Y", "%B %d, %Y"):
            try:
                return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        try:
            parsed = parsedate_to_datetime(raw)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError, OverflowError):
            continue
    return datetime.now(timezone.utc)


async def _x_oembed_one(client: httpx.AsyncClient, post_url: str, run_id: str) -> SocialEventIn:
    # The official oEmbed API is public and unauthenticated. Try the supplied X
    # URL first, then the twitter.com equivalent because legacy embed backends
    # occasionally behave differently across the two hostnames.
    candidates = [post_url]
    if "x.com/" in post_url:
        candidates.append(post_url.replace("x.com/", "twitter.com/", 1))

    payload = None
    last_status = 0
    for candidate in candidates:
        response = await client.get(
            "https://publish.x.com/oembed",
            params={"url": candidate, "omit_script": "true", "theme": "dark", "dnt": "true"},
        )
        last_status = response.status_code
        if response.status_code == 200:
            payload = response.json()
            break
        if response.status_code == 429:
            raise ConnectorError("X oEmbed rate-limited this request.", "RATE_LIMITED")
    if payload is None:
        state = "PERMISSION_REQUIRED" if last_status in {401, 403, 404} else "DEGRADED"
        raise ConnectorError(f"X oEmbed could not fetch this public post (HTTP {last_status}).", state)

    html = str(payload.get("html") or "")
    soup = BeautifulSoup(html, "html.parser")
    blockquote = soup.find("blockquote") or soup
    paragraph = blockquote.find("p")
    text = paragraph.get_text(" ", strip=True) if paragraph else blockquote.get_text(" ", strip=True)
    author = str(payload.get("author_name") or "").strip() or "X author"
    author_url = str(payload.get("author_url") or "").strip()
    username_match = re.search(r"(?:x\.com|twitter\.com)/([^/?#]+)", author_url)
    username = username_match.group(1) if username_match else author
    hashtags, mentions, urls = _extract_text_entities(text)
    status_id = _x_status_id(post_url)

    return SocialEventIn(
        platform="x",
        source_event_id=f"oembed:{status_id}",
        event_type="public_oembed_post",
        author_platform_id=username,
        author_display=author,
        text=text,
        created_at=_parse_x_date(blockquote),
        url=post_url,
        conversation_id=status_id,
        mentions=mentions,
        hashtags=hashtags,
        urls=urls,
        engagement={},
        public_profile={
            "username": username,
            "author_url": author_url or None,
            "oembed_html": html,
            "provider_name": payload.get("provider_name"),
            "provider_url": payload.get("provider_url"),
            "collection_scope": "official_x_oembed_public_post",
            "free_fallback": "official_oembed",
        },
        source_mode="LIVE",
        connector_run_id=run_id,
    )


async def x_oembed_or_bridge(query: str, target: str = "", limit: int = 25) -> list[SocialEventIn]:
    """Free official X post ingestion when explicit public Post URLs are supplied.

    If no X Post URL is supplied, preserve the existing configured RSS/Atom bridge
    behavior. This never claims to provide free global X search.
    """
    post_urls = _extract_x_urls("\n".join([query or "", target or ""]))
    if not post_urls:
        return await _x_public_bridge_original(query, target, limit)

    run_id = f"x-oembed-{uuid4().hex[:10]}"
    async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers={"User-Agent": "NEXUS-SIH26152/0.4"}) as client:
        results = await asyncio.gather(
            *(_x_oembed_one(client, url, run_id) for url in post_urls[:limit]),
            return_exceptions=True,
        )

    output: list[SocialEventIn] = []
    errors: list[str] = []
    for result in results:
        if isinstance(result, Exception):
            errors.append(str(result)[:180])
        else:
            output.append(result)
    if not output and errors:
        raise ConnectorError("X public post URLs could not be fetched: " + " | ".join(errors[:3]), "DEGRADED")
    return output
