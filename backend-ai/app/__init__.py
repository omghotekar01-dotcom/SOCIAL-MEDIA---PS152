"""NEXUS FastAPI analytics package for SIH26152.

Stable public contracts are preserved while hardened implementations replace
older internal functions before FastAPI/collector modules import them.
"""

from . import analytics as analytics
from . import connectors as connectors
from . import free_connectors as free_connectors
from .priority_free_connectors import telegram_monitored_search, x_oembed_or_bridge
from .resilient_connectors import instagram_resilient_profile, mastodon_resilient_search, reddit_resilient_search
from .stable_alerts import stable_alerts
from .stable_views import stable_network, stable_timeline
from .youtube_official import youtube_official_search

# Replay-stable alert identifiers and chart/graph implementations that remain
# useful even for tiny live workspaces.
analytics.alerts = stable_alerts
analytics.timeline = stable_timeline
analytics.build_network = stable_network

# Video-first official YouTube implementation everywhere, including collector runs.
connectors.youtube_search = youtube_official_search

# Preserve route signatures while strengthening public/fallback behavior.
free_connectors.telegram_public_channel = telegram_monitored_search
free_connectors.x_public_bridge = x_oembed_or_bridge
free_connectors.reddit_public_search = reddit_resilient_search
free_connectors.mastodon_search = mastodon_resilient_search
free_connectors.instagram_public_profile = instagram_resilient_profile
