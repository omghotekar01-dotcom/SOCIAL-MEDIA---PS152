"""NEXUS FastAPI analytics package for SIH26152.

Stable public contracts are preserved while hardened implementations replace
older internal functions before FastAPI/collector modules import them.
"""

from . import analytics as analytics
from . import connectors as connectors
from . import free_connectors as free_connectors
from .priority_free_connectors import telegram_monitored_search, x_oembed_or_bridge
from .stable_alerts import stable_alerts
from .youtube_official import youtube_official_search

# Make alert identifiers replay-stable so an alert returned by `/api/alerts` can
# be resolved by `/api/certificates/alert/{id}` on a later independent request.
analytics.alerts = stable_alerts

# Preserve the connector API while using the video-first YouTube implementation
# everywhere, including continuous collection.
connectors.youtube_search = youtube_official_search

# Keep the public connector route signatures stable while upgrading behavior:
# - Telegram accepts a monitored-channel specification with optional workspace query.
# - X accepts explicit public Post URLs through official unauthenticated oEmbed,
#   falling back to the configured permitted RSS/Atom bridge when no URL is given.
free_connectors.telegram_public_channel = telegram_monitored_search
free_connectors.x_public_bridge = x_oembed_or_bridge
