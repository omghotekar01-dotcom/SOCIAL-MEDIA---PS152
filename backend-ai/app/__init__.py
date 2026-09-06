"""NEXUS FastAPI analytics package for SIH26152.

Stable public contracts are preserved while hardened implementations replace
older internal functions before FastAPI/collector modules import them.
"""

from . import analytics as analytics
from . import connectors as connectors
from .stable_alerts import stable_alerts
from .youtube_official import youtube_official_search

# Make alert identifiers replay-stable so an alert returned by `/api/alerts` can
# be resolved by `/api/certificates/alert/{id}` on a later independent request.
analytics.alerts = stable_alerts

# Preserve the connector API while using the video-first YouTube implementation
# everywhere, including continuous collection.
connectors.youtube_search = youtube_official_search
