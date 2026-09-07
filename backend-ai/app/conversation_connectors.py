from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from bs4 import BeautifulSoup

from .free_connectors import (
    USER_AGENT,
    _extract_text_entities,
    _parse_datetime,
    _safe_int,
    bluesky_search as _base_bluesky_search,
)
from .resilient_connectors import mastodon_resilient_search as _base_mastodon_search
from .resilient_connectors import reddit_resilient_search as _base_reddit_search
from .schemas import SocialEventIn


def _clean_html(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(BeautifulSoup(html.unescape(value), "html.parser").get_text(" ", strip=True).split())


def _copy_root_conversation(event: SocialEventIn) -> SocialEventIn:
    profile = dict(event.public_profile or {})
    profile["conversation_collection"] = "root_plus_public_replies_best_effort"
    return event.model_copy(update={"conversation_id": event.source_event_id, "public_profile": profile})


async def bluesky_search_with_replies(query: str, limit: int = 25) -> list[SocialEventIn]:
    roots = await _base_bluesky_search(query, limit)
    if not roots:
        return roots

    output: list[SocialEventIn] = [_copy_root_conversation(root) for root in roots]
    run_id = f"bsky-thread-{uuid4().hex[:10]}"
    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": USER_AGENT}) as client:
        for root in output[: min(5, len(output))]:
            did = str(root.author_platform_id or "")
            rkey = (root.url or "").rstrip("/").rsplit("/", 1)[-1]
            if not did.startswith("did:") or not rkey:
                continue
            uri = f"at://{did}/app.bsky.feed.post/{rkey}"
            try:
                response = await client.get(
                    "https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread",
                    params={"uri": uri, "depth": 1, "parentHeight": 0},
                )
            except httpx.HTTPError:
                continue
            if response.status_code >= 400:
                continue
            thread = response.json().get("thread") or {}
            for index, reply_node in enumerate((thread.get("replies") or [])[:12], start=1):
                post = reply_node.get("post") or {}
                record = post.get("record") or {}
                text = str(record.get("text") or "").strip()
                author = post.get("author") or {}
                reply_uri = str(post.get("uri") or "")
                reply_cid = str(post.get("cid") or reply_uri or f"{root.source_event_id}:{index}")
                handle = str(author.get("handle") or author.get("displayName") or "unknown")
                reply_rkey = reply_uri.rsplit("/", 1)[-1] if "/" in reply_uri else reply_cid
                if not text:
                    continue
                hashtags, mentions, urls = _extract_text_entities(text)
                output.append(
                    SocialEventIn(
                        platform="bluesky",
                        source_event_id=reply_cid,
                        event_type="reply",
                        author_platform_id=str(author.get("did") or handle),
                        author_display=handle,
                        text=text,
                        created_at=_parse_datetime(record.get("createdAt") or post.get("indexedAt")),
                        url=f"https://bsky.app/profile/{handle}/post/{reply_rkey}",
                        parent_event_id=root.source_event_id,
                        conversation_id=root.source_event_id,
                        mentions=mentions,
                        hashtags=hashtags,
                        urls=urls,
                        engagement={
                            "likes": _safe_int(post.get("likeCount")),
                            "reposts": _safe_int(post.get("repostCount")),
                            "replies": _safe_int(post.get("replyCount")),
                        },
                        public_profile={"collection_scope": "public_atproto_thread_reply"},
                        source_mode="LIVE",
                        connector_run_id=run_id,
                    )
                )
    return output


async def mastodon_search_with_replies(query: str, limit: int = 25, base_url: str | None = None) -> list[SocialEventIn]:
    roots = await _base_mastodon_search(query, limit, base_url)
    if not roots:
        return roots
    output: list[SocialEventIn] = [_copy_root_conversation(root) for root in roots]
    run_id = f"mastodon-context-{uuid4().hex[:10]}"

    async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        for root in output[: min(5, len(output))]:
            profile = root.public_profile or {}
            candidate = str(profile.get("resilient_instance_selection") or "").rstrip("/")
            if not candidate:
                instance = str(profile.get("instance") or "").strip()
                candidate = f"https://{instance}" if instance else ""
            if not candidate:
                continue
            try:
                response = await client.get(f"{candidate}/api/v1/statuses/{root.source_event_id}/context")
            except httpx.HTTPError:
                continue
            if response.status_code >= 400:
                continue
            for status in (response.json().get("descendants") or [])[:12]:
                status_id = str(status.get("id") or "")
                text = _clean_html(str(status.get("content") or ""))
                account = status.get("account") or {}
                if not status_id or not text:
                    continue
                hashtags = [str(tag.get("name") or "").lower() for tag in status.get("tags", []) if tag.get("name")]
                mentions = [str(item.get("acct") or "") for item in status.get("mentions", []) if item.get("acct")]
                _, _, urls = _extract_text_entities(text)
                output.append(
                    SocialEventIn(
                        platform="mastodon",
                        source_event_id=status_id,
                        event_type="reply",
                        author_platform_id=str(account.get("id") or account.get("acct") or "unknown"),
                        author_display=str(account.get("acct") or account.get("display_name") or "unknown"),
                        text=text,
                        language=status.get("language"),
                        created_at=_parse_datetime(status.get("created_at")),
                        url=str(status.get("url") or "") or None,
                        parent_event_id=str(status.get("in_reply_to_id") or root.source_event_id),
                        conversation_id=root.source_event_id,
                        mentions=mentions,
                        hashtags=hashtags,
                        urls=urls,
                        engagement={
                            "favourites": _safe_int(status.get("favourites_count")),
                            "reblogs": _safe_int(status.get("reblogs_count")),
                            "replies": _safe_int(status.get("replies_count")),
                        },
                        public_profile={"instance": urlparse(candidate).netloc, "collection_scope": "public_status_context_reply"},
                        source_mode="LIVE",
                        connector_run_id=run_id,
                    )
                )
    return output


def _reddit_comment_events(payload: object, root: SocialEventIn, run_id: str) -> list[SocialEventIn]:
    if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], dict):
        return []
    children = ((payload[1].get("data") or {}).get("children") or [])[:15]
    output: list[SocialEventIn] = []
    for child in children:
        if not isinstance(child, dict) or child.get("kind") != "t1":
            continue
        data = child.get("data") or {}
        comment_id = str(data.get("id") or "")
        text = str(data.get("body") or "").strip()
        if not comment_id or not text or text in {"[deleted]", "[removed]"}:
            continue
        created = float(data.get("created_utc") or 0)
        output.append(
            SocialEventIn(
                platform="reddit",
                source_event_id=f"comment:{comment_id}",
                event_type="comment",
                author_platform_id=str(data.get("author_fullname") or data.get("author") or "unknown"),
                author_display=str(data.get("author") or "unknown"),
                text=text,
                created_at=datetime.fromtimestamp(created, tz=timezone.utc) if created else datetime.now(timezone.utc),
                url=f"https://www.reddit.com{data.get('permalink')}" if str(data.get("permalink") or "").startswith("/") else root.url,
                parent_event_id=root.source_event_id,
                conversation_id=root.source_event_id,
                engagement={"score": _safe_int(data.get("score"))},
                public_profile={"subreddit": data.get("subreddit"), "collection_scope": "public_comment_thread"},
                source_mode="LIVE",
                connector_run_id=run_id,
            )
        )
    return output


async def reddit_search_with_comments(query: str, limit: int = 25) -> list[SocialEventIn]:
    roots = await _base_reddit_search(query, limit)
    if not roots:
        return roots
    output = [_copy_root_conversation(root) for root in roots]
    run_id = f"reddit-comments-{uuid4().hex[:10]}"
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers=headers) as client:
        for root in output[: min(5, len(output))]:
            post_id = root.source_event_id.replace("free:", "")
            try:
                response = await client.get(
                    f"https://www.reddit.com/comments/{post_id}.json",
                    params={"limit": 15, "sort": "top", "raw_json": 1},
                )
            except httpx.HTTPError:
                continue
            if response.status_code >= 400:
                continue
            try:
                output.extend(_reddit_comment_events(response.json(), root, run_id))
            except ValueError:
                continue
    return output
