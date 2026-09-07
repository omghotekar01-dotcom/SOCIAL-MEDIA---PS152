from __future__ import annotations

import asyncio

from app import connectors


class FakeResponse:
    status_code = 200
    text = ''

    def __init__(self, update_id: int, message_id: int):
        self._update_id = update_id
        self._message_id = message_id

    def json(self):
        return {
            'ok': True,
            'result': [
                {
                    'update_id': self._update_id,
                    'message': {
                        'message_id': self._message_id,
                        'date': 1_700_000_000,
                        'chat': {'id': -100123, 'username': 'demo_channel'},
                        'from': {'id': 55, 'username': 'demo_user', 'language_code': 'en'},
                        'text': f'live update {self._message_id}',
                    },
                }
            ],
        }


class FakeAsyncClient:
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
        response = FakeResponse(self.__class__.next_update_id, self.__class__.next_message_id)
        self.__class__.next_update_id += 1
        self.__class__.next_message_id += 1
        return response


def test_telegram_poll_advances_offset(monkeypatch):
    monkeypatch.setattr(connectors.SETTINGS, 'telegram_bot_token', 'demo-token')
    monkeypatch.setattr(connectors.SETTINGS, 'telegram_allowed_chat_ids', '')
    monkeypatch.setattr(connectors.httpx, 'AsyncClient', FakeAsyncClient)
    connectors.TELEGRAM_UPDATE_OFFSET = 0
    FakeAsyncClient.calls = []
    FakeAsyncClient.next_update_id = 10
    FakeAsyncClient.next_message_id = 1

    first = asyncio.run(connectors.telegram_poll(20))
    second = asyncio.run(connectors.telegram_poll(20))

    assert len(first) == 1
    assert len(second) == 1
    assert 'offset' not in FakeAsyncClient.calls[0]
    assert FakeAsyncClient.calls[1]['offset'] == 11
    assert connectors.TELEGRAM_UPDATE_OFFSET == 12
