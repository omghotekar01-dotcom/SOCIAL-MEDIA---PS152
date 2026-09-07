"""NEXUS FastAPI analytics package for SIH26152.

Stable public contracts are preserved while hardened implementations replace
older internal functions before FastAPI/collector modules import them.
"""

from . import analytics as analytics
from . import connectors as connectors
from . import free_connectors as free_connectors
from .priority_free_connectors import telegram_monitored_search
from .resilient_connectors import instagram_resilient_profile, mastodon_resilient_search, reddit_resilient_search
from .conversation_connectors import bluesky_search_with_replies, mastodon_search_with_replies, reddit_search_with_comments
from .stable_alerts import stable_alerts
from .stable_views import stable_network, stable_timeline
from .x_embed_resilience import x_resilient_oembed_or_bridge
from .youtube_official import youtube_official_search

# Backward-compatible public name retained for older preflight/tests/imports while
# the active implementation is the hardened multi-endpoint X oEmbed connector.
x_oembed_or_bridge = x_resilient_oembed_or_bridge

# Replay-stable alert identifiers and chart/graph implementations that remain
# useful even for tiny live workspaces.
analytics.alerts = stable_alerts
analytics.timeline = stable_timeline
analytics.build_network = stable_network

# Video-first official YouTube implementation everywhere, including collector runs.
connectors.youtube_search = youtube_official_search

# Preserve route signatures while strengthening public/fallback behavior.
free_connectors.telegram_public_channel = telegram_monitored_search
free_connectors.x_public_bridge = x_resilient_oembed_or_bridge
free_connectors.bluesky_search = bluesky_search_with_replies
free_connectors.reddit_public_search = reddit_search_with_comments
free_connectors.mastodon_search = mastodon_search_with_replies
free_connectors.instagram_public_profile = instagram_resilient_profile
