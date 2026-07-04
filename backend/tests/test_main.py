from fastapi.testclient import TestClient

try:
    from backend.app.main import app
except ModuleNotFoundError:
    from app.main import app

client = TestClient(app)


def test_healthcheck() -> None:
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_lead_control_center() -> None:
    response = client.get('/lead-control-center')
    assert response.status_code == 200
    assert 'Lead Control Center' in response.text
    assert 'Render web service' in response.text


def test_api_health() -> None:
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'healthy'


def test_scraper_queue() -> None:
    response = client.get('/api/scraper-queue')
    assert response.status_code == 200
    data = response.json()
    assert {'queued', 'running', 'failedLast24h'} <= data.keys()


def test_lead_stats() -> None:
    response = client.get('/api/lead-stats')
    assert response.status_code == 200
    data = response.json()
    assert {'today', 'week', 'total'} <= data.keys()


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
