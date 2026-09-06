from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_and_connector_contracts_load_without_credentials():
    health = client.get('/health')
    assert health.status_code == 200
    assert health.json()['version'] == '0.3.0'

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
