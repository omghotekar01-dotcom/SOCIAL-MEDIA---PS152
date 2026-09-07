from __future__ import annotations

import asyncio

from app import youtube_official
from app.schemas import YouTubeSearchRequest


class FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = ''

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None, **kwargs):
        if url.endswith('/search'):
            return FakeResponse(200, {
                'items': [{
                    'id': {'videoId': 'abc123'},
                    'snippet': {
                        'publishedAt': '2026-09-06T12:00:00Z',
                        'channelId': 'channel-1',
                        'channelTitle': 'Demo Channel',
                        'title': 'RiverLink update',
                        'description': 'Public update about #RiverLinkUpdate',
                    },
                }],
            })
        # Simulate a normal YouTube case where comments are disabled/restricted.
        return FakeResponse(403, {})


def test_video_is_kept_when_comments_are_disabled(monkeypatch):
    monkeypatch.setattr(youtube_official.SETTINGS, 'youtube_api_key', 'demo-key')
    monkeypatch.setattr(youtube_official.httpx, 'AsyncClient', FakeClient)

    events = asyncio.run(youtube_official.youtube_official_search(
        YouTubeSearchRequest(query='RiverLink', max_videos=1, max_comments_per_video=10)
    ))

    assert len(events) == 1
    event = events[0]
    assert event.platform == 'youtube'
    assert event.event_type == 'video'
    assert event.source_event_id == 'video:abc123'
    assert event.conversation_id == 'abc123'
    assert event.source_mode == 'LIVE'
    assert event.url == 'https://www.youtube.com/watch?v=abc123'
    assert 'RiverLink update' in event.text
