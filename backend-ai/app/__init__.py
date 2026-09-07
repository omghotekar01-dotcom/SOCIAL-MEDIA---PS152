"""NEXUS FastAPI analytics package for SIH26152.

Stable public contracts are preserved while hardened implementations replace
older internal functions before FastAPI/collector modules import them.
"""

from . import analytics as analytics
from . import connectors as connectors
from . import free_connectors as free_connectors
from .scalable_clusters import scalable_assign_clusters
from .telegram_rich import telegram_rich_poll
from .youtube_staged import youtube_staged_search

# Patch connector + clustering functions first. Collector modules bind these with
# `from ... import ...`, so ordering matters. Exact YouTube URLs use a fast-first
# sample and continue exhaustive provider-bounded collection in the background.
connectors.telegram_poll = telegram_rich_poll
connectors.youtube_search = youtube_staged_search
analytics.assign_clusters = scalable_assign_clusters

# Patch analysis primitives before alert_engine/stable_alerts are imported. This
# ensures alerts, narratives, API routes and continuous collection all use the
# same full-population implementations instead of stale function references.
from .advanced_analytics import advanced_demographics, advanced_infer_text, advanced_trend_metrics
from .stable_views import stable_network, stable_timeline
from .complete_narratives import complete_narrative_summaries

analytics.infer_text = advanced_infer_text
analytics.demographics = advanced_demographics
analytics.trend_metrics = advanced_trend_metrics
analytics.timeline = stable_timeline
analytics.build_network = stable_network
analytics.narrative_summaries = complete_narrative_summaries

from .complete_demo import complete_seed_demo_events
from .complete_overview import complete_overview

analytics.seed_demo_events = complete_seed_demo_events
analytics.overview = complete_overview

# Import reaction-aware alerts only after narrative/trend/network functions above
# are bound, because alert_engine imports those names during module initialization.
from .complete_alerts import complete_alerts

analytics.alerts = complete_alerts

# Collector now binds the hardened connector + scalable cluster functions.
from .advanced_collector import AdvancedCollectorManager, AdvancedCollectorStartRequest
from .conversation_connectors import mastodon_search_with_replies, reddit_search_with_comments
from .priority_free_connectors import telegram_monitored_search
from .relationship_enrichment import bluesky_search_with_relationships
from .resilient_connectors import instagram_resilient_profile, mastodon_resilient_search, reddit_resilient_search
from .x_embed_resilience import x_resilient_oembed_or_bridge

# Backward-compatible public name retained for older preflight/tests/imports while
# the active implementation is the hardened multi-endpoint X oEmbed connector.
x_oembed_or_bridge = x_resilient_oembed_or_bridge

# Preserve route signatures while strengthening public/fallback behavior and
# collecting linked public replies/comments where the provider exposes them.
free_connectors.telegram_public_channel = telegram_monitored_search
free_connectors.x_public_bridge = x_resilient_oembed_or_bridge
free_connectors.bluesky_search = bluesky_search_with_relationships
free_connectors.reddit_public_search = reddit_search_with_comments
free_connectors.mastodon_search = mastodon_search_with_replies
free_connectors.instagram_public_profile = instagram_resilient_profile

# Main imports CollectorStartRequest/COLLECTOR from .collector after package init.
# Replace those symbols up-front so the API transparently receives the richer
# continuous multi-source collector without breaking existing frontend contracts.
from . import collector as collector

collector.CollectorStartRequest = AdvancedCollectorStartRequest
collector.COLLECTOR = AdvancedCollectorManager()
