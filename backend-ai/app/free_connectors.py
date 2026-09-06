from __future__ import annotations

import asyncio
import hashlib
import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote, urlparse
from uuid import uuid4

import httpx
from bs4 import BeautifulSoup

from .config import get_settings
from .connectors import ConnectorError
from .schemas import SocialEventIn

SETTINGS = get_settings()
USER_AGENT = "NEXUS-SIH26152/0.3 (+public-social-intelligence-prototype)"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return _now()
    raw = value.strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(raw)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError, OverflowError):
            return _now()


def _safe_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    raw = str(value).strip().lower().replace(",", "")
    multiplier = 1
    if raw.endswith("k"):
        multiplier, raw = 1_000, raw[:-1]
    elif raw.endswith("m"):
        multiplier, raw = 1_000_000, raw[:-1]
    try:
        return int(float(raw) * multiplier)
    except ValueError:
        return 0


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(BeautifulSoup(html.unescape(value), "html.parser").get_text(" ", strip=True).split())


def _stable_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8", errors="ignore")).hexdigest()[:24]


def _extract_text_entities(text: str) -> tuple[list[str], list[str], list[str]]:
    hashtags = sorted({m.group(1).lower() for m in re.finditer(r"(?<!\w)#([\w-]{2,80})", text, re.UNICODE)})
    mentions = sorted({m.group(1).lower() for m in re.finditer(r"(?<!\w)@([A-Za-z0-9_.-]{2,80})", text)})
    urls = sorted({m.group(0).rstrip(".,;:!?)]}") for m in re.finditer(r"https?://[^\s<>()\[\]{}\"']+", text, re.I)})
    return hashtags, mentions, urls


def parse_telegram_public_html(channel: str, page_html: str, limit: int = 25) -> list[SocialEventIn]:
    """Parse Telegram's public channel preview page without login/API keys.

    Kept as a pure function so the parser is deterministic and unit-testable.
    Telegram can change public HTML at any time; callers expose that as DEGRADED
    rather than pretending collection succeeded.
    """
    channel = channel.strip().lstrip("@").strip("/")
    soup = BeautifulSoup(page_html, "html.parser")
    output: list[SocialEventIn] = []
    run_id = f"tg-public-{uuid4().hex[:10]}"

    for wrap in soup.select(".tgme_widget_message_wrap"):
        message = wrap.select_one(".tgme_widget_message")
        if message is None:
            continue
        data_post = str(message.get("data-post") or "")
        if "/" not in data_post:
            continue
        resolved_channel, message_id = data_post.rsplit("/", 1)
        resolved_channel = resolved_channel.lstrip("@").strip("/") or channel
        text_node = wrap.select_one(".tgme_widget_message_text")
        text = _clean_text(str(text_node)) if text_node else ""
        if not text:
            media_caption = wrap.select_one(".tgme_widget_message_caption")
            text = _clean_text(str(media_caption)) if media_caption else ""
        if not text:
            continue
        time_node = wrap.select_one("time[datetime]")
        created_at = _parse_datetime(str(time_node.get("datetime")) if time_node else None)
        views_node = wrap.select_one(".tgme_widget_message_views")
        views = _safe_int(views_node.get_text(strip=True) if views_node else 0)
        author_node = wrap.select_one(".tgme_widget_message_author")
        author = _clean_text(str(author_node)) if author_node else resolved_channel
        permalink = f"https://t.me/{resolved_channel}/{message_id}"
        hashtags, mentions, urls = _extract_text_entities(text)
        output.append(
            SocialEventIn(
                platform="telegram",
                source_event_id=f"public:{resolved_channel}:{message_id}",
                event_type="public_channel_post",
                author_platform_id=resolved_channel,
                author_display=author or resolved_channel,
                text=text,
                created_at=created_at,
                url=permalink,
                conversation_id=resolved_channel,
                mentions=mentions,
                hashtags=hashtags,
                urls=urls,
                engagement={"views": views},
                public_profile={"channel": resolved_channel, "collection_scope": "public_preview"},
                source_mode="LIVE",
                connector_run_id=run_id,
            )
        )
        if len(output) >= limit:
            break
    return output


async def telegram_public_channel(channel: str, limit: int = 25) -> list[SocialEventIn]:
    channel = channel.strip().lstrip("@").strip("/")
    if not channel or not re.fullmatch(r"[A-Za-z0-9_]{4,64}", channel):
        raise ConnectorError("Enter a valid public Telegram channel username, for example 'mychannel'.", "ERROR")
    url = f"https://t.me/s/{quote(channel)}"
    try:
        async with httpx.AsyncClient(timeout=SETTINGS.public_http_timeout_seconds, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            response = await client.get(url)
    except httpx.HTTPError as exc:
        raise ConnectorError(f"Telegram public preview could not be reached: {exc}", "DEGRADED") from exc
    if response.status_code == 429:
        raise ConnectorError("Telegram public preview rate-limited this request.", "RATE_LIMITED")
    if response.status_code in {401, 403, 404}:
        raise ConnectorError("Channel is unavailable, private, restricted, or not exposed through Telegram public preview.", "PERMISSION_REQUIRED")
    if response.status_code >= 400:
        raise ConnectorError(f"Telegram public preview returned HTTP {response.status_code}.", "DEGRADED")
    events = parse_telegram_public_html(channel, response.text, limit)
    if not events:
        raise ConnectorError("No public posts were found. The channel may be empty or Telegram may have changed the preview markup.", "DEGRADED")
    return events


def parse_rss_or_atom(platform: str, body: str, limit: int = 25, run_id: str | None = None) -> list[SocialEventIn]:
    """Parse RSS/Atom from an explicitly configured public bridge."""
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise ConnectorError("Configured public bridge did not return valid RSS/Atom XML.", "DEGRADED") from exc

    output: list[SocialEventIn] = []
    run_id = run_id or f"{platform}-bridge-{uuid4().hex[:10]}"
    entries = list(root.findall(".//item"))
    if not entries:
        entries = list(root.findall(".//{http://www.w3.org/2005/Atom}entry"))

    for entry in entries[:limit]:
        def find_text(*names: str) -> str:
            for name in names:
                node = entry.find(name)
                if node is not None and node.text:
                    return node.text.strip()
            return ""

        title = find_text("title", "{http://www.w3.org/2005/Atom}title")
        description = find_text("description", "summary", "content", "{http://www.w3.org/2005/Atom}summary", "{http://www.w3.org/2005/Atom}content")
        text = _clean_text(description or title)
        link = find_text("link")
        atom_link = entry.find("{http://www.w3.org/2005/Atom}link")
        if not link and atom_link is not None:
            link = str(atom_link.get("href") or "")
        guid = find_text("guid", "id", "{http://www.w3.org/2005/Atom}id") or link or _stable_id(platform, text)
        pubdate = find_text("pubDate", "published", "updated", "{http://www.w3.org/2005/Atom}published", "{http://www.w3.org/2005/Atom}updated")
        creator = find_text("author", "creator", "{http://www.w3.org/2005/Atom}author") or platform
        if not text:
            continue
        hashtags, mentions, urls = _extract_text_entities(text)
        output.append(
            SocialEventIn(
                platform=platform,  # type: ignore[arg-type]
                source_event_id=f"bridge:{_stable_id(guid)}",
                event_type="public_bridge_item",
                author_platform_id=creator,
                author_display=creator,
                text=text,
                created_at=_parse_datetime(pubdate),
                url=link or None,
                mentions=mentions,
                hashtags=hashtags,
                urls=urls,
                public_profile={"collection_scope": "configured_public_bridge"},
                source_mode="LIVE",
                connector_run_id=run_id,
            )
        )
    return output


async def _configured_bridge(platform: str, template: str, query: str, target: str, limit: int) -> list[SocialEventIn]:
    if not template.strip():
        raise ConnectorError(
            f"No {platform.upper()} public bridge is configured. Use the official connector, configure the bridge template, or import public exports.",
            "CREDENTIALS_REQUIRED" if platform == "x" else "PERMISSION_REQUIRED",
        )
    url = template.replace("{query}", quote(query)).replace("{target}", quote(target))
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConnectorError(f"Configured {platform} bridge template produced an invalid URL.", "ERROR")
    try:
        async with httpx.AsyncClient(timeout=SETTINGS.public_http_timeout_seconds, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            response = await client.get(url)
    except httpx.HTTPError as exc:
        raise ConnectorError(f"Configured {platform} public bridge could not be reached: {exc}", "DEGRADED") from exc
    if response.status_code == 429:
        raise ConnectorError(f"Configured {platform} public bridge rate-limited the request.", "RATE_LIMITED")
    if response.status_code >= 400:
        raise ConnectorError(f"Configured {platform} public bridge returned HTTP {response.status_code}.", "DEGRADED")
    events = parse_rss_or_atom(platform, response.text, limit)
    if not events:
        raise ConnectorError(f"Configured {platform} public bridge returned no parseable items.", "DEGRADED")
    return events


async def x_public_bridge(query: str, target: str = "", limit: int = 25) -> list[SocialEventIn]:
    return await _configured_bridge("x", SETTINGS.x_public_rss_url_template, query, target, limit)


async def instagram_public_bridge(query: str = "", target: str = "", limit: int = 25) -> list[SocialEventIn]:
    if SETTINGS.instagram_public_rss_url_template:
        return await _configured_bridge("instagram", SETTINGS.instagram_public_rss_url_template, query, target, limit)
    return await instagram_public_profile(target or query, limit)


async def instagram_public_profile(profile: str, limit: int = 20) -> list[SocialEventIn]:
    """Best-effort Instaloader fallback for genuinely public profiles.

    Instagram frequently changes unauthenticated access. Failure is deliberately
    surfaced as DEGRADED/PERMISSION_REQUIRED; this path never bypasses login or
    private-account controls.
    """
    profile = profile.strip().lstrip("@").strip("/")
    if not profile or not re.fullmatch(r"[A-Za-z0-9._]{1,30}", profile):
        raise ConnectorError("Enter a valid public Instagram profile username.", "ERROR")

    def collect() -> list[SocialEventIn]:
        try:
            import instaloader
        except ImportError as exc:
            raise ConnectorError("Instaloader fallback is not installed.", "DISABLED") from exc
        loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            quiet=True,
        )
        try:
            account = instaloader.Profile.from_username(loader.context, profile)
            if account.is_private:
                raise ConnectorError("Instagram profile is private; NEXUS does not bypass private-account controls.", "PERMISSION_REQUIRED")
            output: list[SocialEventIn] = []
            run_id = f"ig-public-{uuid4().hex[:10]}"
            for post in account.get_posts():
                caption = post.caption or ""
                if not caption.strip():
                    continue
                hashtags, mentions, urls = _extract_text_entities(caption)
                shortcode = post.shortcode
                output.append(
                    SocialEventIn(
                        platform="instagram",
                        source_event_id=f"public:{profile}:{shortcode}",
                        event_type="public_profile_post",
                        author_platform_id=str(account.userid),
                        author_display=profile,
                        text=caption,
                        created_at=post.date_utc.replace(tzinfo=timezone.utc),
                        url=f"https://www.instagram.com/p/{shortcode}/",
                        mentions=mentions,
                        hashtags=hashtags,
                        urls=urls,
                        engagement={"likes": int(post.likes or 0), "comments": int(post.comments or 0)},
                        public_profile={"profile": profile, "collection_scope": "public_profile"},
                        source_mode="LIVE",
                        connector_run_id=run_id,
                    )
                )
                if len(output) >= limit:
                    break
            return output
        except ConnectorError:
            raise
        except Exception as exc:  # external library changes are expected
            raise ConnectorError(f"Instagram public-profile fallback is unavailable: {str(exc)[:220]}", "DEGRADED") from exc

    return await asyncio.to_thread(collect)


async def youtube_free_search(query: str, limit: int = 10) -> list[SocialEventIn]:
    """Zero-key public YouTube metadata search through yt-dlp.

    This intentionally returns video metadata, not comments. The official
    YouTube Data API remains the richer path when a free quota key is available.
    """
    if not query.strip():
        raise ConnectorError("YouTube query cannot be empty.", "ERROR")

    def collect() -> list[SocialEventIn]:
        try:
            import yt_dlp
        except ImportError as exc:
            raise ConnectorError("yt-dlp fallback is not installed.", "DISABLED") from exc
        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": True,
            "playlistend": limit,
            "socket_timeout": SETTINGS.public_http_timeout_seconds,
        }
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
        except Exception as exc:
            raise ConnectorError(f"YouTube zero-key fallback could not search public metadata: {str(exc)[:220]}", "DEGRADED") from exc
        output: list[SocialEventIn] = []
        run_id = f"yt-free-{uuid4().hex[:10]}"
        for item in (info or {}).get("entries") or []:
            if not item:
                continue
            video_id = str(item.get("id") or "")
            if not video_id:
                continue
            title = str(item.get("title") or "")
            description = str(item.get("description") or "")
            text = " — ".join(part for part in [title, description] if part).strip()
            if not text:
                continue
            uploader = str(item.get("uploader") or item.get("channel") or "YouTube")
            timestamp = item.get("timestamp") or item.get("release_timestamp")
            created_at = datetime.fromtimestamp(timestamp, tz=timezone.utc) if timestamp else _now()
            webpage = str(item.get("url") or "")
            if not webpage.startswith("http"):
                webpage = f"https://www.youtube.com/watch?v={video_id}"
            hashtags, mentions, urls = _extract_text_entities(text)
            output.append(
                SocialEventIn(
                    platform="youtube",
                    source_event_id=f"free:{video_id}",
                    event_type="video_metadata",
                    author_platform_id=str(item.get("channel_id") or uploader),
                    author_display=uploader,
                    text=text,
                    created_at=created_at,
                    url=webpage,
                    conversation_id=video_id,
                    mentions=mentions,
                    hashtags=hashtags,
                    urls=urls,
                    engagement={
                        "views": _safe_int(item.get("view_count")),
                        "likes": _safe_int(item.get("like_count")),
                        "comments": _safe_int(item.get("comment_count")),
                    },
                    public_profile={"collection_scope": "public_video_metadata", "free_fallback": "yt-dlp"},
                    source_mode="LIVE",
                    connector_run_id=run_id,
                )
            )
        if not output:
            raise ConnectorError("YouTube zero-key fallback returned no public video metadata.", "DEGRADED")
        return output

    return await asyncio.to_thread(collect)


async def bluesky_search(query: str, limit: int = 25) -> list[SocialEventIn]:
    if not query.strip():
        raise ConnectorError("Bluesky query cannot be empty.", "ERROR")
    endpoint = "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"
    try:
        async with httpx.AsyncClient(timeout=SETTINGS.public_http_timeout_seconds, headers={"User-Agent": USER_AGENT}) as client:
            response = await client.get(endpoint, params={"q": query, "limit": min(limit, 100), "sort": "latest"})
    except httpx.HTTPError as exc:
        raise ConnectorError(f"Bluesky public API could not be reached: {exc}", "DEGRADED") from exc
    if response.status_code == 429:
        raise ConnectorError("Bluesky public API rate limit reached.", "RATE_LIMITED")
    if response.status_code >= 400:
        raise ConnectorError(f"Bluesky public API returned HTTP {response.status_code}.", "DEGRADED")
    output: list[SocialEventIn] = []
    run_id = f"bsky-{uuid4().hex[:10]}"
    for post in response.json().get("posts", [])[:limit]:
        record = post.get("record") or {}
        text = str(record.get("text") or "")
        uri = str(post.get("uri") or "")
        cid = str(post.get("cid") or "")
        author = post.get("author") or {}
        handle = str(author.get("handle") or author.get("displayName") or "unknown")
        rkey = uri.rsplit("/", 1)[-1] if "/" in uri else cid
        if not text or not rkey:
            continue
        hashtags, mentions, urls = _extract_text_entities(text)
        output.append(
            SocialEventIn(
                platform="bluesky",
                source_event_id=cid or uri or _stable_id(handle, text),
                event_type="post",
                author_platform_id=str(author.get("did") or handle),
                author_display=handle,
                text=text,
                created_at=_parse_datetime(record.get("createdAt") or post.get("indexedAt")),
                url=f"https://bsky.app/profile/{handle}/post/{rkey}",
                mentions=mentions,
                hashtags=hashtags,
                urls=urls,
                engagement={
                    "likes": _safe_int(post.get("likeCount")),
                    "reposts": _safe_int(post.get("repostCount")),
                    "replies": _safe_int(post.get("replyCount")),
                    "quotes": _safe_int(post.get("quoteCount")),
                },
                public_profile={"collection_scope": "public_atproto"},
                source_mode="LIVE",
                connector_run_id=run_id,
            )
        )
    return output


async def reddit_public_search(query: str, limit: int = 25) -> list[SocialEventIn]:
    if not query.strip():
        raise ConnectorError("Reddit query cannot be empty.", "ERROR")
    endpoint = "https://www.reddit.com/search.json"
    params = {"q": query, "limit": min(limit, 100), "sort": "new", "raw_json": 1}
    try:
        async with httpx.AsyncClient(timeout=SETTINGS.public_http_timeout_seconds, follow_redirects=True, headers={"User-Agent": SETTINGS.reddit_user_agent or USER_AGENT}) as client:
            response = await client.get(endpoint, params=params)
    except httpx.HTTPError as exc:
        raise ConnectorError(f"Reddit public search could not be reached: {exc}", "DEGRADED") from exc
    if response.status_code == 429:
        raise ConnectorError("Reddit public endpoint rate-limited this request.", "RATE_LIMITED")
    if response.status_code in {401, 403}:
        raise ConnectorError("Reddit public JSON access is restricted from this network; configure OAuth/import instead.", "PERMISSION_REQUIRED")
    if response.status_code >= 400:
        raise ConnectorError(f"Reddit public endpoint returned HTTP {response.status_code}.", "DEGRADED")
    output: list[SocialEventIn] = []
    run_id = f"reddit-{uuid4().hex[:10]}"
    children = response.json().get("data", {}).get("children", [])
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
        output.append(
            SocialEventIn(
                platform="reddit",
                source_event_id=post_id,
                event_type="submission",
                author_platform_id=str(data.get("author_fullname") or data.get("author") or "unknown"),
                author_display=str(data.get("author") or "unknown"),
                text=text,
                created_at=datetime.fromtimestamp(float(data.get("created_utc") or 0), tz=timezone.utc),
                url=url or None,
                conversation_id=str(data.get("subreddit") or ""),
                mentions=mentions,
                hashtags=hashtags,
                urls=urls,
                engagement={"score": _safe_int(data.get("score")), "comments": _safe_int(data.get("num_comments")), "upvote_ratio": data.get("upvote_ratio")},
                public_profile={"subreddit": data.get("subreddit"), "collection_scope": "public_json"},
                source_mode="LIVE",
                connector_run_id=run_id,
            )
        )
    return output


async def mastodon_search(query: str, limit: int = 25, base_url: str | None = None) -> list[SocialEventIn]:
    if not query.strip():
        raise ConnectorError("Mastodon query cannot be empty.", "ERROR")
    base = (base_url or SETTINGS.mastodon_base_url).strip().rstrip("/")
    parsed = urlparse(base)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConnectorError("MASTODON_BASE_URL is invalid.", "ERROR")
    try:
        async with httpx.AsyncClient(timeout=SETTINGS.public_http_timeout_seconds, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            response = await client.get(f"{base}/api/v2/search", params={"q": query, "type": "statuses", "limit": min(limit, 40), "resolve": "false"})
    except httpx.HTTPError as exc:
        raise ConnectorError(f"Mastodon instance could not be reached: {exc}", "DEGRADED") from exc
    if response.status_code == 429:
        raise ConnectorError("Mastodon instance rate-limited the request.", "RATE_LIMITED")
    if response.status_code in {401, 403}:
        raise ConnectorError("This Mastodon instance requires authenticated search; choose a public-search instance or import data.", "PERMISSION_REQUIRED")
    if response.status_code >= 400:
        raise ConnectorError(f"Mastodon instance returned HTTP {response.status_code}.", "DEGRADED")
    output: list[SocialEventIn] = []
    run_id = f"mastodon-{uuid4().hex[:10]}"
    for status in response.json().get("statuses", [])[:limit]:
        status_id = str(status.get("id") or "")
        text = _clean_text(str(status.get("content") or ""))
        account = status.get("account") or {}
        if not status_id or not text:
            continue
        hashtags = [str(t.get("name") or "").lower() for t in status.get("tags", []) if t.get("name")]
        mentions = [str(m.get("acct") or "") for m in status.get("mentions", []) if m.get("acct")]
        _, _, urls = _extract_text_entities(text)
        output.append(
            SocialEventIn(
                platform="mastodon",
                source_event_id=status_id,
                event_type="status",
                author_platform_id=str(account.get("id") or account.get("acct") or "unknown"),
                author_display=str(account.get("acct") or account.get("display_name") or "unknown"),
                text=text,
                language=status.get("language"),
                created_at=_parse_datetime(status.get("created_at")),
                url=str(status.get("url") or "") or None,
                mentions=mentions,
                hashtags=hashtags,
                urls=urls,
                engagement={
                    "favourites": _safe_int(status.get("favourites_count")),
                    "reblogs": _safe_int(status.get("reblogs_count")),
                    "replies": _safe_int(status.get("replies_count")),
                },
                public_profile={"instance": parsed.netloc, "collection_scope": "public_instance_api"},
                source_mode="LIVE",
                connector_run_id=run_id,
            )
        )
    return output
