from __future__ import annotations

import asyncio

from app import meta_discovery


class FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = ''

    def json(self):
        return self._payload


class FakeClient:
    calls: list[tuple[str, dict]] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None, **kwargs):
        self.__class__.calls.append((url, dict(params or {})))
        if url.endswith('/ig_hashtag_search'):
            return FakeResponse(200, {'data': [{'id': 'hashtag-42'}]})
        if url.endswith('/hashtag-42/recent_media'):
            return FakeResponse(200, {
                'data': [{
                    'id': 'media-7',
                    'caption': 'Verified public #RiverLinkUpdate post',
                    'timestamp': '2026-09-06T12:30:00Z',
                    'permalink': 'https://www.instagram.com/p/demo/',
                    'like_count': 12,
                    'comments_count': 3,
                    'media_type': 'IMAGE',
                }],
            })
        return FakeResponse(404, {})


def test_instagram_hashtag_search_uses_official_two_step_flow(monkeypatch):
    monkeypatch.setattr(meta_discovery.SETTINGS, 'meta_access_token', 'demo-token')
    monkeypatch.setattr(meta_discovery.SETTINGS, 'meta_instagram_account_id', 'ig-user-1')
    monkeypatch.setattr(meta_discovery.httpx, 'AsyncClient', FakeClient)
    FakeClient.calls = []

    events = asyncio.run(meta_discovery.instagram_hashtag_search('#RiverLinkUpdate', 10))

    assert len(events) == 1
    event = events[0]
    assert event.platform == 'instagram'
    assert event.event_type == 'hashtag_recent_media'
    assert event.source_event_id == 'hashtag:media-7'
    assert event.source_mode == 'LIVE'
    assert event.engagement['likes'] == 12
    assert event.public_profile['queried_hashtag'] == 'RiverLinkUpdate'
    assert FakeClient.calls[0][0].endswith('/ig_hashtag_search')
    assert FakeClient.calls[0][1]['q'] == 'RiverLinkUpdate'
    assert FakeClient.calls[1][0].endswith('/hashtag-42/recent_media')
    assert FakeClient.calls[1][1]['user_id'] == 'ig-user-1'
