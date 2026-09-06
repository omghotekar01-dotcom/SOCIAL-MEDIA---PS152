from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_and_connector_contracts_load_without_credentials():
    health = client.get('/health')
    assert health.status_code == 200
    assert health.json()['version'] == '0.4.0'

    response = client.get('/api/connectors/status')
    assert response.status_code == 200
    connectors = {item['platform']: item for item in response.json()['connectors']}
    for platform in {'x', 'telegram', 'instagram', 'youtube', 'bluesky', 'reddit', 'mastodon', 'replay'}:
        assert platform in connectors
    assert connectors['telegram']['state'] == 'READY'
    assert connectors['bluesky']['state'] == 'READY'


def test_public_connector_validation_fails_cleanly_before_network():
    response = client.post('/api/connectors/telegram/public', json={'channel': '***', 'limit': 10})
    assert response.status_code in {400, 422, 503}

    response = client.post('/api/connectors/x/public', json={'query': '', 'target': '', 'limit': 10})
    assert response.status_code == 400


def test_fresh_workspace_search_clears_previous_topic_without_network_calls():
    seeded = client.post('/api/demo/seed', json={'reset': True})
    assert seeded.status_code == 200
    assert seeded.json()['total_events'] > 0

    fresh = client.post(
        '/api/search/workspace',
        json={
            'query': 'brand new isolated topic',
            'reset': True,
            'limit_per_source': 5,
            'enable_youtube': False,
            'enable_bluesky': False,
            'enable_reddit': False,
            'enable_mastodon': False,
        },
    )
    assert fresh.status_code == 200
    body = fresh.json()
    assert body['query'] == 'brand new isolated topic'
    assert body['reset'] is True
    assert body['total_events'] == 0
    assert body['sources'] == {}

    overview = client.get('/api/overview')
    assert overview.status_code == 200
    assert overview.json()['total_events'] == 0
