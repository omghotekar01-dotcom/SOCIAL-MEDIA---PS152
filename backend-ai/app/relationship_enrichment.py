from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .conversation_connectors import bluesky_search_with_replies
from .free_connectors import USER_AGENT
from .schemas import SocialEventIn


async def bluesky_search_with_relationships(query: str, limit: int = 25) -> list[SocialEventIn]:
    """Collect Bluesky posts/replies and best-effort public follow relationships.

    The public AT Protocol graph endpoint is queried only for a small number of
    observed authors. Returned handles are stored as provenance metadata and are
    used by the network layer only when both ends of the relationship are present
    in the collected evidence workspace.
    """
    events = await bluesky_search_with_replies(query, limit)
    if not events:
        return events

    authors: dict[str, list[SocialEventIn]] = {}
    for event in events:
        did = str(event.author_platform_id or "")
        if did.startswith("did:"):
            authors.setdefault(did, []).append(event)
        if len(authors) >= 8:
            break

    async def fetch_follows(client: httpx.AsyncClient, did: str) -> tuple[str, list[str], str | None]:
        try:
            response = await client.get(
                "https://public.api.bsky.app/xrpc/app.bsky.graph.getFollows",
                params={"actor": did, "limit": 50},
            )
        except httpx.HTTPError as exc:
            return did, [], str(exc)[:120]
        if response.status_code >= 400:
            return did, [], f"HTTP {response.status_code}"
        handles = [
            str(item.get("handle") or "").lower().lstrip("@")
            for item in response.json().get("follows", [])
            if item.get("handle")
        ]
        return did, list(dict.fromkeys(handles))[:50], None

    async with httpx.AsyncClient(timeout=12, headers={"User-Agent": USER_AGENT}) as client:
        results = await asyncio.gather(*(fetch_follows(client, did) for did in authors), return_exceptions=False)

    for did, handles, error in results:
        for event in authors.get(did, []):
            profile: dict[str, Any] = dict(event.public_profile or {})
            if handles:
                profile["observed_following_handles"] = handles
                profile["relationship_collection_scope"] = "public_atproto_getFollows"
            elif error:
                profile["relationship_collection_note"] = f"Public follow lookup unavailable for this author: {error}"
            event.public_profile = profile

    return events
