from __future__ import annotations

from app.free_connectors import parse_rss_or_atom, parse_telegram_public_html


TELEGRAM_HTML = """
<html><body>
  <div class="tgme_widget_message_wrap">
    <div class="tgme_widget_message" data-post="demo_channel/42">
      <div class="tgme_widget_message_author">Demo Channel</div>
      <div class="tgme_widget_message_text">Major #RiverLink update from @fieldteam https://example.org/evidence</div>
      <span class="tgme_widget_message_views">1.2K</span>
      <time datetime="2026-09-06T12:30:00+00:00"></time>
    </div>
  </div>
</body></html>
"""

RSS_XML = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>Demo</title>
<item>
  <title>Cross-platform #RiverLink claim</title>
  <description>Public post mentioning @source and https://example.org/item</description>
  <link>https://example.org/post/1</link>
  <guid>demo-1</guid>
  <pubDate>Sun, 06 Sep 2026 12:30:00 GMT</pubDate>
  <author>analyst@example.org</author>
</item>
</channel></rss>
"""


def test_public_telegram_parser_normalizes_evidence():
    events = parse_telegram_public_html("demo_channel", TELEGRAM_HTML, 10)
    assert len(events) == 1
    event = events[0]
    assert event.platform == "telegram"
    assert event.source_mode == "LIVE"
    assert event.source_event_id == "public:demo_channel:42"
    assert event.url == "https://t.me/demo_channel/42"
    assert event.engagement["views"] == 1200
    assert "riverlink" in event.hashtags
    assert "fieldteam" in event.mentions
    assert "https://example.org/evidence" in event.urls


def test_public_bridge_parser_preserves_live_provenance():
    events = parse_rss_or_atom("x", RSS_XML, 10, run_id="test-run")
    assert len(events) == 1
    event = events[0]
    assert event.platform == "x"
    assert event.source_mode == "LIVE"
    assert event.connector_run_id == "test-run"
    assert event.url == "https://example.org/post/1"
    assert event.event_type == "public_bridge_item"
