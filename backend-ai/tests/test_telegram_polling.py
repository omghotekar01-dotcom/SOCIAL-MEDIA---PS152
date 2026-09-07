from __future__ import annotations

import asyncio

from app import connectors, telegram_rich


class FakeResponse:
    status_code = 200
    text = ''

    def __init__(self, payload: dict):
        self._payload = payload

    def json(self):
        return self._payload


class OffsetClient:
    calls: list[dict] = []
    next_update_id = 10
    next_message_id = 1

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, endpoint, params=None, **kwargs):
        self.__class__.calls.append(dict(params or {}))
        payload = {
            'ok': True,
            'result': [{
                'update_id': self.__class__.next_update_id,
                'message': {
                    'message_id': self.__class__.next_message_id,
                    'date': 1_700_000_000,
                    'chat': {'id': -100123, 'username': 'demo_group', 'type': 'supergroup'},
                    'from': {'id': 55, 'username': 'demo_user', 'language_code': 'en'},
                    'text': f'live update {self.__class__.next_message_id}',
                },
            }],
        }
        self.__class__.next_update_id += 1
        self.__class__.next_message_id += 1
        return FakeResponse(payload)


def test_telegram_poll_advances_offset(monkeypatch):
    monkeypatch.setattr(connectors.SETTINGS, 'telegram_bot_token', 'demo-token')
    monkeypatch.setattr(connectors.SETTINGS, 'telegram_allowed_chat_ids', '')
    monkeypatch.setattr(telegram_rich.httpx, 'AsyncClient', OffsetClient)
    connectors.TELEGRAM_UPDATE_OFFSET = 0
    telegram_rich.TELEGRAM_CONVERSATION_CACHE.clear()
    OffsetClient.calls = []
    OffsetClient.next_update_id = 10
    OffsetClient.next_message_id = 1

    first = asyncio.run(connectors.telegram_poll(20))
    second = asyncio.run(connectors.telegram_poll(20))

    assert len(first) == 1
    assert len(second) == 1
    assert 'offset' not in OffsetClient.calls[0]
    assert OffsetClient.calls[1]['offset'] == 11
    assert connectors.TELEGRAM_UPDATE_OFFSET == 12


class DiscussionClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, endpoint, params=None, **kwargs):
        return FakeResponse({
            'ok': True,
            'result': [
                {
                    'update_id': 101,
                    'channel_post': {
                        'message_id': 7,
                        'date': 1_700_000_000,
                        'chat': {'id': -100111, 'username': 'NexusSIHDemo', 'title': 'NexusSIHDemo', 'type': 'channel'},
                        'sender_chat': {'id': -100111, 'username': 'NexusSIHDemo', 'title': 'NexusSIHDemo'},
                        'text': 'Root channel post about RiverLink',
                    },
                },
                {
                    'update_id': 102,
                    'message': {
                        'message_id': 50,
                        'date': 1_700_000_010,
                        'chat': {'id': -100222, 'username': 'NexusDiscussion', 'title': 'Nexus Discussion', 'type': 'supergroup'},
                        'is_automatic_forward': True,
                        'sender_chat': {'id': -100111, 'username': 'NexusSIHDemo', 'title': 'NexusSIHDemo'},
                        'forward_origin': {
                            'type': 'channel',
                            'chat': {'id': -100111, 'username': 'NexusSIHDemo', 'type': 'channel'},
                            'message_id': 7,
                            'date': 1_700_000_000,
                        },
                        'text': 'Root channel post about RiverLink',
                    },
                },
                {
                    'update_id': 103,
                    'message': {
                        'message_id': 51,
                        'date': 1_700_000_020,
                        'chat': {'id': -100222, 'username': 'NexusDiscussion', 'title': 'Nexus Discussion', 'type': 'supergroup'},
                        'from': {'id': 77, 'username': 'viewer_one', 'language_code': 'en'},
                        'text': 'I think this claim is wrong and worrying',
                        'reply_to_message': {
                            'message_id': 50,
                            'date': 1_700_000_010,
                            'chat': {'id': -100222, 'type': 'supergroup'},
                            'is_automatic_forward': True,
                            'forward_origin': {
                                'type': 'channel',
                                'chat': {'id': -100111, 'username': 'NexusSIHDemo', 'type': 'channel'},
                                'message_id': 7,
                                'date': 1_700_000_000,
                            },
                        },
                    },
                },
            ],
        })


def test_discussion_comment_links_to_original_channel_post(monkeypatch):
    monkeypatch.setattr(connectors.SETTINGS, 'telegram_bot_token', 'demo-token')
    monkeypatch.setattr(connectors.SETTINGS, 'telegram_allowed_chat_ids', '')
    monkeypatch.setattr(telegram_rich.httpx, 'AsyncClient', DiscussionClient)
    connectors.TELEGRAM_UPDATE_OFFSET = 0
    telegram_rich.TELEGRAM_CONVERSATION_CACHE.clear()

    events = asyncio.run(connectors.telegram_poll(20))

    # Automatic discussion forward dedupes to the same channel source id.
    roots = [event for event in events if event.source_event_id == '-100111:7']
    assert len(roots) == 1
    root = roots[0]
    assert root.conversation_id == '-100111:7'

    comment = next(event for event in events if event.source_event_id == '-100222:51')
    assert comment.event_type == 'discussion_reply'
    assert comment.parent_event_id == '-100111:7'
    assert comment.conversation_id == '-100111:7'
    assert comment.public_profile['collection_scope'] == 'telegram_linked_discussion_comment'
