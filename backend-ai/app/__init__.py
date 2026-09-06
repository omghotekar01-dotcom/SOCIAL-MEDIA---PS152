"""NEXUS FastAPI analytics package for SIH26152.

The package keeps connector-specific upgrades behind the stable connector API so
callers such as the continuous collector and FastAPI routes do not need to know
which implementation version is active.
"""

from . import connectors as connectors
from .youtube_official import youtube_official_search

# Preserve the public connector contract while using the video-first YouTube
# implementation everywhere. This also fixes continuous collection because
# collector.py imports youtube_search from the same connector module.
connectors.youtube_search = youtube_official_search
