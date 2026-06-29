from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_healthcheck() -> None:
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_mock_leads_limit() -> None:
    response = client.get('/api/leads/mock?limit=3')
    assert response.status_code == 200
    data = response.json()
    assert len(data['leads']) == 3


def test_mock_leads_limit_bounds() -> None:
    response = client.get('/api/leads/mock?limit=500')
    assert response.status_code == 200
    data = response.json()
    assert len(data['leads']) == 50
