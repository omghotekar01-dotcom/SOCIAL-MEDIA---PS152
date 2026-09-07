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


class DisabledCommentsClient:
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
                    'id': {'videoId': 'abc123def45'},
                    'snippet': {'title': 'search result'},
                }],
            })
        if url.endswith('/videos'):
            return FakeResponse(200, {
                'items': [{
                    'id': 'abc123def45',
                    'status': {'privacyStatus': 'public'},
                    'statistics': {'viewCount': '1000', 'likeCount': '80', 'commentCount': '12'},
                    'snippet': {
                        'publishedAt': '2026-09-06T12:00:00Z',
                        'channelId': 'channel-1',
                        'channelTitle': 'Demo Channel',
                        'title': 'RiverLink update',
                        'description': 'Public update about #RiverLinkUpdate',
                        'thumbnails': {'high': {'url': 'https://img.example/high.jpg'}},
                    },
                }],
            })
        if url.endswith('/commentThreads'):
            return FakeResponse(403, {'error': {'errors': [{'reason': 'commentsDisabled'}]}})
        return FakeResponse(404, {})


def test_video_is_kept_when_comments_are_disabled(monkeypatch):
    monkeypatch.setattr(youtube_official.SETTINGS, 'youtube_api_key', 'demo-key')
    monkeypatch.setattr(youtube_official.httpx, 'AsyncClient', DisabledCommentsClient)

    events = asyncio.run(youtube_official.youtube_official_search(
        YouTubeSearchRequest(query='RiverLink', max_videos=1, max_comments_per_video=10)
    ))

    assert len(events) == 1
    event = events[0]
    assert event.platform == 'youtube'
    assert event.event_type == 'video'
    assert event.source_event_id == 'video:abc123def45'
    assert event.conversation_id == 'abc123def45'
    assert event.source_mode == 'LIVE'
    assert event.url == 'https://www.youtube.com/watch?v=abc123def45'
    assert 'RiverLink update' in event.text
    assert event.public_profile['comments_state'] == 'disabled'


class RichCommentsClient:
    calls: list[tuple[str, dict]] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None, **kwargs):
        self.__class__.calls.append((url, dict(params or {})))
        if url.endswith('/search'):
            return FakeResponse(200, {
                'items': [
                    {'id': {'videoId': 'zero0000000'}, 'snippet': {}},
                    {'id': {'videoId': 'rich1111111'}, 'snippet': {}},
                ]
            })
        if url.endswith('/videos'):
            return FakeResponse(200, {
                'items': [
                    {
                        'id': 'zero0000000',
                        'status': {'privacyStatus': 'public'},
                        'statistics': {'commentCount': '0'},
                        'snippet': {'title': 'No comments', 'channelTitle': 'Quiet', 'publishedAt': '2026-09-06T10:00:00Z'},
                    },
                    {
                        'id': 'rich1111111',
                        'status': {'privacyStatus': 'public'},
                        'statistics': {'viewCount': '5000', 'likeCount': '400', 'commentCount': '50'},
                        'snippet': {'title': 'Comment rich', 'channelTitle': 'Active', 'publishedAt': '2026-09-06T11:00:00Z'},
                    },
                ]
            })
        if url.endswith('/commentThreads'):
            assert params['videoId'] == 'rich1111111'
            return FakeResponse(200, {
                'items': [{
                    'id': 'thread-1',
                    'snippet': {
                        'totalReplyCount': 2,
                        'topLevelComment': {
                            'id': 'top-1',
                            'snippet': {
                                'textDisplay': 'This is worrying',
                                'authorDisplayName': 'viewer1',
                                'publishedAt': '2026-09-06T12:01:00Z',
                                'likeCount': 4,
                            },
                        },
                    },
                    'replies': {
                        'comments': [{
                            'id': 'reply-1',
                            'snippet': {
                                'textDisplay': 'I agree',
                                'authorDisplayName': 'viewer2',
                                'publishedAt': '2026-09-06T12:02:00Z',
                                'likeCount': 1,
                            },
                        }]
                    },
                }]
            })
        if url.endswith('/comments'):
            assert params['parentId'] == 'top-1'
            return FakeResponse(200, {
                'items': [
                    {
                        'id': 'reply-1',
                        'snippet': {'textDisplay': 'I agree', 'authorDisplayName': 'viewer2', 'publishedAt': '2026-09-06T12:02:00Z'},
                    },
                    {
                        'id': 'reply-2',
                        'snippet': {'textDisplay': 'This seems false', 'authorDisplayName': 'viewer3', 'publishedAt': '2026-09-06T12:03:00Z'},
                    },
                ]
            })
        return FakeResponse(404, {})


def test_search_prefers_comment_rich_video_and_links_replies(monkeypatch):
    monkeypatch.setattr(youtube_official.SETTINGS, 'youtube_api_key', 'demo-key')
    monkeypatch.setattr(youtube_official.httpx, 'AsyncClient', RichCommentsClient)
    RichCommentsClient.calls = []

    events = asyncio.run(youtube_official.youtube_official_search(
        YouTubeSearchRequest(query='RiverLink', max_videos=1, max_comments_per_video=10)
    ))

    assert events[0].source_event_id == 'video:rich1111111'
    assert events[0].public_profile['comments_state'] == 'available'
    assert events[0].public_profile['captured_comment_count'] == 3

    top = next(event for event in events if event.source_event_id == 'comment:top-1')
    reply1 = next(event for event in events if event.source_event_id == 'reply:reply-1')
    reply2 = next(event for event in events if event.source_event_id == 'reply:reply-2')
    assert top.parent_event_id == 'video:rich1111111'
    assert reply1.parent_event_id == 'comment:top-1'
    assert reply2.parent_event_id == 'comment:top-1'
    assert all(event.conversation_id == 'rich1111111' for event in (top, reply1, reply2))


def test_direct_youtube_url_bypasses_search(monkeypatch):
    monkeypatch.setattr(youtube_official.SETTINGS, 'youtube_api_key', 'demo-key')
    monkeypatch.setattr(youtube_official.httpx, 'AsyncClient', RichCommentsClient)
    RichCommentsClient.calls = []

    events = asyncio.run(youtube_official.youtube_official_search(
        YouTubeSearchRequest(query='https://www.youtube.com/watch?v=rich1111111', max_videos=3, max_comments_per_video=5)
    ))

    assert events[0].source_event_id == 'video:rich1111111'
    assert not any(url.endswith('/search') for url, _ in RichCommentsClient.calls)


class PaginatedCommentsClient:
    calls: list[tuple[str, dict]] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None, **kwargs):
        params = dict(params or {})
        self.__class__.calls.append((url, params))
        if url.endswith('/videos'):
            return FakeResponse(200, {
                'items': [{
                    'id': 'page1111111',
                    'status': {'privacyStatus': 'public'},
                    'statistics': {'commentCount': '4'},
                    'snippet': {
                        'title': 'Paged conversation',
                        'channelTitle': 'Paged Channel',
                        'publishedAt': '2026-09-06T10:00:00Z',
                    },
                }]
            })
        if url.endswith('/commentThreads'):
            if params.get('pageToken') == 'thread-page-2':
                return FakeResponse(200, {
                    'items': [{
                        'id': 'thread-2',
                        'snippet': {
                            'totalReplyCount': 0,
                            'topLevelComment': {
                                'id': 'top-2',
                                'snippet': {
                                    'textDisplay': 'Second page comment',
                                    'authorDisplayName': 'viewer4',
                                    'publishedAt': '2026-09-06T12:04:00Z',
                                },
                            },
                        },
                    }]
                })
            return FakeResponse(200, {
                'items': [{
                    'id': 'thread-1',
                    'snippet': {
                        'totalReplyCount': 2,
                        'topLevelComment': {
                            'id': 'top-1',
                            'snippet': {
                                'textDisplay': 'First page comment',
                                'authorDisplayName': 'viewer1',
                                'publishedAt': '2026-09-06T12:01:00Z',
                            },
                        },
                    },
                }],
                'nextPageToken': 'thread-page-2',
            })
        if url.endswith('/comments'):
            if params.get('pageToken') == 'reply-page-2':
                return FakeResponse(200, {
                    'items': [{
                        'id': 'reply-2',
                        'snippet': {
                            'textDisplay': 'Second reply page',
                            'authorDisplayName': 'viewer3',
                            'publishedAt': '2026-09-06T12:03:00Z',
                        },
                    }]
                })
            return FakeResponse(200, {
                'items': [{
                    'id': 'reply-1',
                    'snippet': {
                        'textDisplay': 'First reply page',
                        'authorDisplayName': 'viewer2',
                        'publishedAt': '2026-09-06T12:02:00Z',
                    },
                }],
                'nextPageToken': 'reply-page-2',
            })
        return FakeResponse(404, {})


def test_exhaustive_mode_follows_all_thread_and_reply_page_tokens(monkeypatch):
    monkeypatch.setattr(youtube_official.SETTINGS, 'youtube_api_key', 'demo-key')
    monkeypatch.setattr(youtube_official.SETTINGS, 'youtube_max_comments_per_video', 0)
    monkeypatch.setattr(youtube_official.SETTINGS, 'youtube_max_comment_pages_per_video', 0)
    monkeypatch.setattr(youtube_official.SETTINGS, 'youtube_max_reply_pages_per_thread', 0)
    monkeypatch.setattr(youtube_official.httpx, 'AsyncClient', PaginatedCommentsClient)
    PaginatedCommentsClient.calls = []

    events = asyncio.run(youtube_official.youtube_official_search(
        YouTubeSearchRequest(
            query='https://youtu.be/page1111111',
            max_videos=1,
            max_comments_per_video=0,
        )
    ))

    root = events[0]
    assert root.source_event_id == 'video:page1111111'
    assert root.public_profile['comments_state'] == 'available'
    assert root.public_profile['captured_comment_count'] == 4
    assert root.public_profile['captured_top_level_comment_count'] == 2
    assert root.public_profile['captured_reply_count'] == 2
    assert root.public_profile['comment_thread_pages_fetched'] == 2
    assert root.public_profile['reply_pages_fetched'] == 2
    assert root.public_profile['collection_complete'] is True
    assert root.public_profile['collection_stop_reason'] == 'provider_exhausted'
    assert root.public_profile['exhaustive_requested'] is True

    assert any(params.get('pageToken') == 'thread-page-2' for url, params in PaginatedCommentsClient.calls if url.endswith('/commentThreads'))
    assert any(params.get('pageToken') == 'reply-page-2' for url, params in PaginatedCommentsClient.calls if url.endswith('/comments'))
