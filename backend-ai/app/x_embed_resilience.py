from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

import httpx
from bs4 import BeautifulSoup

from .connectors import ConnectorError
from .free_connectors import _extract_text_entities, _stable_id, x_public_bridge as _original_public_bridge
from .schemas import SocialEventIn

# Accept the normal URLs copied from desktop/mobile X and legacy Twitter.
_X_STATUS_RE = re.compile(
    r"https?://(?:(?:www|mobile)\.)?(?:x\.com|twitter\.com)/[A-Za-z0-9_]+/status/\d+(?:\?[^\s,]*)?",
    re.I,
)


def extract_x_post_urls(value: str) -> list[str]:
    urls: list[str] = []
    for match in _X_STATUS_RE.finditer(value or ""):
        raw = match.group(0).rstrip(".,;:!?)\"]}")
        parsed = urlparse(raw)
        # Tracking/query parameters are unnecessary for oEmbed and occasionally
        # make copied share URLs fail, so use a canonical status permalink.
        canonical = urlunparse(("https", parsed.netloc.lower(), parsed.path.rstrip("/"), "", "", ""))
        canonical = re.sub(r"https://(?:www\.|mobile\.)?twitter\.com/", "https://twitter.com/", canonical, flags=re.I)
        canonical = re.sub(r"https://(?:www\.|mobile\.)?x\.com/", "https://x.com/", canonical, flags=re.I)
        if canonical not in urls:
            urls.append(canonical)
    return urls[:50]


def _status_id(url: str) -> str:
    match = re.search(r"/status/(\d+)", url)
    return match.group(1) if match else _stable_id(url)


def _parse_date(blockquote: BeautifulSoup) -> datetime:
    for anchor in reversed(blockquote.find_all("a")):
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
            pass
    return datetime.now(timezone.utc)


def _candidate_urls(post_url: str) -> list[str]:
    """Generate X/Twitter permalink variants for the same public post."""
    parsed = urlparse(post_url)
    path = parsed.path.rstrip("/")
    variants = [f"https://x.com{path}", f"https://twitter.com{path}"]
    return list(dict.fromkeys(variants))


async def _fetch_oembed(client: httpx.AsyncClient, post_url: str) -> dict:
    # X currently documents publish.x.com/oembed. The legacy publish.twitter.com
    # endpoint remains useful for compatibility with some x.com copied links.
    endpoints = ["https://publish.x.com/oembed", "https://publish.twitter.com/oembed"]
    attempts: list[str] = []
    for candidate in _candidate_urls(post_url):
        for endpoint in endpoints:
            try:
                response = await client.get(
                    endpoint,
                    params={"url": candidate, "omit_script": "1", "dnt": "true"},
                )
            except httpx.HTTPError as exc:
                attempts.append(f"{urlparse(endpoint).netloc}: network {str(exc)[:80]}")
                continue
            if response.status_code == 200:
                try:
                    payload = response.json()
                except ValueError:
                    attempts.append(f"{urlparse(endpoint).netloc}: invalid JSON")
                    continue
                if payload.get("html"):
                    payload["_nexus_endpoint"] = endpoint
                    payload["_nexus_candidate_url"] = candidate
                    return payload
                attempts.append(f"{urlparse(endpoint).netloc}: empty embed")
                continue
            if response.status_code == 429:
                raise ConnectorError("X oEmbed rate-limited this request. Retry shortly.", "RATE_LIMITED")
            attempts.append(f"{urlparse(endpoint).netloc}: HTTP {response.status_code}")

    raise ConnectorError(
        "The public X Post could not be embedded. It may be deleted, protected, age/login restricted, or temporarily unavailable. "
        + " | ".join(attempts[-4:]),
        "PERMISSION_REQUIRED",
    )


def _readable_oembed_text(blockquote: BeautifulSoup, author: str) -> tuple[str, bool, list[str]]:
    """Return usable text without rejecting GIF/image/video-only public posts."""
    paragraph = blockquote.find("p")
    text = paragraph.get_text(" ", strip=True) if paragraph else blockquote.get_text(" ", strip=True)
    text = " ".join(text.split()).strip()
    if text:
        return text, False, []

    alt_candidates: list[str] = []
    for image in blockquote.find_all("img"):
        alt = str(image.get("alt") or "").strip()
        if alt and alt.lower() not in {"image", "photo", "gif"} and alt not in alt_candidates:
            alt_candidates.append(alt)
    if alt_candidates:
        return " · ".join(alt_candidates[:3]), True, alt_candidates[:3]

    # Some X posts are literally media-only. Rejecting them made valid public
    # GIF/video posts disappear from NEXUS. Keep the evidence and disclose that
    # X supplied an embed but no textual caption; downstream NLP should therefore
    # treat the placeholder as low-information rather than claimed post wording.
    return f"[Media-only X post by {author}; no readable caption returned by X oEmbed]", True, []


async def _one(client: httpx.AsyncClient, post_url: str, run_id: str) -> SocialEventIn:
    payload = await _fetch_oembed(client, post_url)
    html = str(payload.get("html") or "")
    soup = BeautifulSoup(html, "html.parser")
    blockquote = soup.find("blockquote") or soup

    author = str(payload.get("author_name") or "").strip() or "X author"
    author_url = str(payload.get("author_url") or "").strip()
    username_match = re.search(r"(?:x\.com|twitter\.com)/([^/?#]+)", author_url, re.I)
    username = username_match.group(1) if username_match else author
    text, media_only, media_alt_text = _readable_oembed_text(blockquote, author)
    hashtags, mentions, urls = _extract_text_entities(text)
    status_id = _status_id(post_url)

    return SocialEventIn(
        platform="x",
        source_event_id=f"oembed:{status_id}",
        event_type="public_oembed_media_post" if media_only else "public_oembed_post",
        author_platform_id=username,
        author_display=author,
        text=text,
        created_at=_parse_date(blockquote),
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
            "oembed_compatibility": "publish_x_then_publish_twitter",
            "oembed_endpoint_used": payload.get("_nexus_endpoint"),
            "oembed_candidate_url": payload.get("_nexus_candidate_url"),
            "media_only": media_only,
            "media_alt_text": media_alt_text,
            "content_disclosure": (
                "X oEmbed exposed the public embed but no readable caption; NEXUS retained a disclosed media-only placeholder."
                if media_only else "Post text parsed from X oEmbed."
            ),
        },
        source_mode="LIVE",
        connector_run_id=run_id,
    )


async def x_resilient_oembed_or_bridge(query: str, target: str = "", limit: int = 25) -> list[SocialEventIn]:
    post_urls = extract_x_post_urls("\n".join([query or "", target or ""]))
    if not post_urls:
        return await _original_public_bridge(query, target, limit)

    run_id = f"x-oembed-{uuid4().hex[:10]}"
    async with httpx.AsyncClient(
        timeout=20,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 NEXUS-SIH26152/0.7"},
    ) as client:
        results = await asyncio.gather(*(_one(client, url, run_id) for url in post_urls[:limit]), return_exceptions=True)

    output: list[SocialEventIn] = []
    errors: list[str] = []
    for result in results:
        if isinstance(result, Exception):
            errors.append(str(result)[:260])
        else:
            output.append(result)

    if not output:
        raise ConnectorError(
            "No supplied public X Post URL could be fetched automatically. X may be refusing embed access for that specific post. "
            "Use NEXUS Manual X Conversation Import to paste the public post/replies as disclosed IMPORT evidence. "
            + (" | ".join(errors[:2]) if errors else "Check that the URL is a public /status/ link."),
            "PERMISSION_REQUIRED",
        )
    return output
