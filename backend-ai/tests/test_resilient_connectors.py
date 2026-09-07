from datetime import datetime, timezone

import pytest

from app.connectors import ConnectorError
from app.resilient_connectors import (
    _reddit_events,
    instagram_resilient_profile,
    mastodon_resilient_search,
    reddit_resilient_search,
)
from app.schemas import SocialEventIn
import app.resilient_connectors as resilient


def event(platform: str = "reddit") -> SocialEventIn:
    return SocialEventIn(
        platform=platform,  # type: ignore[arg-type]
        source_event_id=f"{platform}:1",
        event_type="post",
        author_display="tester",
        text="RiverLink public discussion",
        created_at=datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc),
        source_mode="LIVE",
    )


def test_reddit_oauth_payload_parser_keeps_public_evidence_fields():
    payload = {
        "data": {
            "children": [
                {
                    "data": {
                        "id": "abc",
                        "title": "RiverLink update",
                        "selftext": "Public discussion #RiverLink",
                        "author": "demo_user",
                        "created_utc": 1788772800,
                        "permalink": "/r/test/comments/abc/demo/",
                        "subreddit": "test",
                        "score": 12,
                        "num_comments": 4,
                        "upvote_ratio": 0.91,
                    }
                }
            ]
        }
    }
    rows = _reddit_events(payload, 10, "oauth_search")
    assert len(rows) == 1
    assert rows[0].platform == "reddit"
    assert rows[0].public_profile["collection_scope"] == "oauth_search"
    assert rows[0].hashtags == ["riverlink"]
    assert rows[0].source_mode == "LIVE"


@pytest.mark.asyncio
async def test_reddit_resilient_search_uses_public_fallback(monkeypatch):
    monkeypatch.setattr(resilient.SETTINGS, "reddit_client_id", "")
    monkeypatch.setattr(resilient.SETTINGS, "reddit_client_secret", "")

    async def fake_public(query: str, limit: int):
        assert query == "RiverLink"
        return [event("reddit")]

    monkeypatch.setattr(resilient, "_base_reddit_public_search", fake_public)
    rows = await reddit_resilient_search("RiverLink", 5)
    assert len(rows) == 1
    assert rows[0].platform == "reddit"


@pytest.mark.asyncio
async def test_mastodon_resilient_search_retries_instances(monkeypatch):
    monkeypatch.setattr(resilient, "_mastodon_candidates", lambda _requested: ["https://one.example", "https://two.example"])
    calls: list[str] = []

    async def fake_search(query: str, limit: int, base_url: str | None = None):
        calls.append(str(base_url))
        if base_url == "https://one.example":
            raise ConnectorError("blocked", "PERMISSION_REQUIRED")
        return [event("mastodon")]

    monkeypatch.setattr(resilient, "_base_mastodon_search", fake_search)
    rows = await mastodon_resilient_search("RiverLink", 5)
    assert calls == ["https://one.example", "https://two.example"]
    assert rows[0].public_profile["resilient_instance_selection"] == "https://two.example"


@pytest.mark.asyncio
async def test_instagram_resilient_profile_prefers_configured_bridge(monkeypatch):
    monkeypatch.setattr(resilient.SETTINGS, "instagram_public_rss_url_template", "https://bridge.example/?q={query}")

    async def fake_bridge(platform: str, template: str, query: str, target: str, limit: int):
        assert platform == "instagram"
        return [event("instagram")]

    async def should_not_run(profile: str, limit: int):
        raise AssertionError("profile fallback should not run when configured bridge succeeds")

    monkeypatch.setattr(resilient, "_configured_bridge", fake_bridge)
    monkeypatch.setattr(resilient, "_base_instagram_public_profile", should_not_run)
    rows = await instagram_resilient_profile("demo", 5)
    assert rows[0].platform == "instagram"
