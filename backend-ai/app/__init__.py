"""NEXUS FastAPI analytics package for SIH26152.

Stable public contracts are preserved while hardened implementations replace
older internal functions before FastAPI/collector modules import them.
"""

from . import analytics as analytics
from . import connectors as connectors
from . import free_connectors as free_connectors
from .advanced_analytics import advanced_demographics, advanced_infer_text, advanced_trend_metrics
from .advanced_collector import AdvancedCollectorManager, AdvancedCollectorStartRequest
from .complete_alerts import complete_alerts
from .complete_demo import complete_seed_demo_events
from .complete_overview import complete_overview
from .conversation_connectors import bluesky_search_with_replies, mastodon_search_with_replies, reddit_search_with_comments
from .priority_free_connectors import telegram_monitored_search
from .resilient_connectors import instagram_resilient_profile, mastodon_resilient_search, reddit_resilient_search
from .stable_views import stable_network, stable_timeline
from .x_embed_resilience import x_resilient_oembed_or_bridge
from .youtube_official import youtube_official_search

# Backward-compatible public name retained for older preflight/tests/imports while
# the active implementation is the hardened multi-endpoint X oEmbed connector.
x_oembed_or_bridge = x_resilient_oembed_or_bridge

# SIH26152 analysis contract: eight emotion dimensions, explicit stance/sarcasm,
# aggregate privacy-conscious demographics, near-term trend momentum, and a
# deterministic reaction-rich jury dataset that is always labelled REPLAY.
analytics.infer_text = advanced_infer_text
analytics.demographics = advanced_demographics
analytics.trend_metrics = advanced_trend_metrics
analytics.overview = complete_overview
analytics.seed_demo_events = complete_seed_demo_events

# Stable chart/graph behavior plus reaction-aware explainable attention alerts.
analytics.alerts = complete_alerts
analytics.timeline = stable_timeline
analytics.build_network = stable_network

# Video-first official YouTube implementation everywhere, including collector runs.
connectors.youtube_search = youtube_official_search

# Preserve route signatures while strengthening public/fallback behavior and
# collecting linked public replies/comments where the provider exposes them.
free_connectors.telegram_public_channel = telegram_monitored_search
free_connectors.x_public_bridge = x_resilient_oembed_or_bridge
free_connectors.bluesky_search = bluesky_search_with_replies
free_connectors.reddit_public_search = reddit_search_with_comments
free_connectors.mastodon_search = mastodon_search_with_replies
free_connectors.instagram_public_profile = instagram_resilient_profile

# Main imports CollectorStartRequest/COLLECTOR from .collector after package init.
# Replace those symbols up-front so the API transparently receives the richer
# continuous multi-source collector without breaking existing frontend contracts.
from . import collector as collector

collector.CollectorStartRequest = AdvancedCollectorStartRequest
collector.COLLECTOR = AdvancedCollectorManager()
