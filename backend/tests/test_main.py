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
    assert 'quality' in data


def test_event_rejects_unknown_event_name() -> None:
    response = client.post('/api/event', json={'event_name': 'random_click'})
    assert response.status_code == 400


def test_event_requires_database_url(monkeypatch) -> None:
    monkeypatch.delenv('DATABASE_URL', raising=False)
    response = client.post(
        '/api/event',
        json={
            'event_name': 'generate_lead',
            'client_id': 'GA4_CLIENT_ID_HERE',
            'visitor_id': 'optional-internal-id',
            'lead_id': 'optional-lead-id',
            'page_url': 'https://example.com/roof-repair',
            'utm_source': 'google',
            'utm_medium': 'organic',
            'utm_campaign': 'pinellas_handyman_leads',
            'event_data': {'form_type': 'quote_request', 'lead_score': 82},
        },
    )
    assert response.status_code == 503
    assert response.json()['ok'] is False


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
