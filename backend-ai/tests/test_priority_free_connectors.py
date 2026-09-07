from datetime import datetime, timezone

from app.priority_free_connectors import _extract_x_urls, _matches_query, _parse_channel_spec
from app.schemas import SocialEventIn, WorkspaceSearchRequest
from app.x_embed_resilience import extract_x_post_urls


def event(text: str) -> SocialEventIn:
    return SocialEventIn(
        platform="telegram",
        source_event_id="test:1",
        event_type="public_channel_post",
        author_display="Demo Channel",
        text=text,
        created_at=datetime(2026, 9, 7, 6, 0, tzinfo=timezone.utc),
        source_mode="LIVE",
    )


def test_telegram_channel_spec_supports_multiple_channels_and_query():
    channels, query = _parse_channel_spec("channel_one,@channel_two;channel_three||AI regulation India")
    assert channels == ["channel_one", "channel_two", "channel_three"]
    assert query == "AI regulation India"


def test_monitored_telegram_posts_are_filtered_by_active_query():
    assert _matches_query(event("Breaking update about AI regulation in India"), "AI regulation")
    assert not _matches_query(event("Weekend cricket match result"), "AI regulation")
    assert _matches_query(event("Follow #RiverLinkUpdate for verified information"), "#RiverLinkUpdate")


def test_workspace_explicit_telegram_target_is_bound_to_query():
    request = WorkspaceSearchRequest(
        query="RiverLink",
        telegram_channel="my_public_channel",
        enable_youtube=False,
        enable_bluesky=False,
        enable_reddit=False,
        enable_mastodon=False,
    )
    assert request.telegram_channel == "my_public_channel||RiverLink"


def test_workspace_defaults_to_nexus_sih_demo_channel():
    request = WorkspaceSearchRequest(
        query="RiverLink",
        telegram_channel=None,
        enable_youtube=False,
        enable_bluesky=False,
        enable_reddit=False,
        enable_mastodon=False,
    )
    assert request.telegram_channel == "NexusSIHDemo||RiverLink"


def test_x_public_post_urls_are_detected_without_accepting_random_urls():
    value = "https://x.com/example/status/1234567890 https://twitter.com/other/status/987654321"
    assert _extract_x_urls(value) == [
        "https://x.com/example/status/1234567890",
        "https://twitter.com/other/status/987654321",
    ]
    assert _extract_x_urls("https://example.com/post/123") == []


def test_resilient_x_url_normalizer_accepts_copied_mobile_and_tracking_links():
    value = (
        "https://www.x.com/example/status/1234567890?s=20 "
        "https://mobile.twitter.com/other/status/987654321?ref_src=twsrc%5Etfw"
    )
    assert extract_x_post_urls(value) == [
        "https://x.com/example/status/1234567890",
        "https://twitter.com/other/status/987654321",
    ]
