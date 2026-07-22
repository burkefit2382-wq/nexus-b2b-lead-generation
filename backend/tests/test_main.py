from pathlib import Path

from fastapi.testclient import TestClient

try:
    from backend.app.main import app
    from backend.app.services import config
    from backend.app.services import hubspot as hubspot_service
except ModuleNotFoundError:
    from app.main import app
    from app.services import config
    from app.services import hubspot as hubspot_service

client = TestClient(app)
SCHEMA_PATH = Path(__file__).resolve().parents[1] / 'db' / 'schema.sql'


def test_healthcheck() -> None:
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'
    assert response.json()['service'] == 'nexus-b2b-lead-generation-api'


def test_lead_control_center() -> None:
    response = client.get('/lead-control-center')
    assert response.status_code == 200
    assert 'Lead Control Center' in response.text
    assert 'Render web service' in response.text


def test_workflow_demo() -> None:
    response = client.get('/workflow-demo')
    assert response.status_code == 200
    assert 'NEXUS Public Workflow Demo' in response.text
    assert 'Lead intelligence pipeline' in response.text


def test_workflow_demo_stylesheet_is_served() -> None:
    response = client.get('/workflow-demo.css')
    assert response.status_code == 200
    assert 'text/css' in response.headers['content-type']
    assert '.workflow-demo-page' in response.text


def test_api_health() -> None:
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'healthy'
    assert response.json()['ready'] == '/ready'
    assert response.json()['metrics'] == '/metrics'


def test_readiness_local_environment() -> None:
    response = client.get('/ready')
    assert response.status_code == 200
    data = response.json()
    assert data['ready'] is True
    assert data['checks']['productionConfigurationEnforced'] is False


def test_readiness_production_requires_configuration(monkeypatch) -> None:
    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.delenv('JWT_SECRET', raising=False)
    monkeypatch.delenv('STRIPE_SECRET_KEY', raising=False)
    monkeypatch.delenv('STRIPE_WEBHOOK_SECRET', raising=False)
    monkeypatch.delenv('PRICE_ID', raising=False)
    monkeypatch.delenv('RESEND_API_KEY', raising=False)
    monkeypatch.delenv('HUBSPOT_ACCESS_TOKEN', raising=False)
    response = client.get('/ready')
    assert response.status_code == 503
    data = response.json()
    assert data['ready'] is False
    assert data['checks']['requiredConfiguration']['databaseUrlConfigured'] is False


def test_metrics_endpoint() -> None:
    response = client.get('/metrics')
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/plain')
    assert 'nexus_service_up{service="nexus-api"} 1' in response.text
    assert 'nexus_scraper_total_records' in response.text


def test_config_status_does_not_expose_secret(monkeypatch) -> None:
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:password@example.com/neondb?sslmode=require')
    monkeypatch.setenv('JWT_SECRET', 'test-secret-value')
    response = client.get('/api/config-status')
    assert response.status_code == 200
    data = response.json()
    assert data['databaseUrlConfigured'] is True
    assert data['jwtConfigured'] is True
    assert 'password' not in response.text
    assert 'example.com' not in response.text
    assert 'test-secret-value' not in response.text


def test_config_status_reports_hubspot(monkeypatch) -> None:
    monkeypatch.setenv('HUBSPOT_ACCESS_TOKEN', 'test-hubspot-token')
    response = client.get('/api/config-status')
    assert response.status_code == 200
    assert response.json()['hubspotConfigured'] is True


def test_hubspot_status_requires_token(monkeypatch) -> None:
    monkeypatch.delenv('HUBSPOT_ACCESS_TOKEN', raising=False)
    monkeypatch.delenv('HUBSPOT_SERVICE_KEY', raising=False)
    monkeypatch.delenv('HUBSPOT_PRIVATE_APP_TOKEN', raising=False)
    monkeypatch.delenv('HUBSPOT_API_KEY', raising=False)
    response = client.get('/api/hubspot-status')
    assert response.status_code == 200
    data = response.json()
    assert data['hubspot']['configured'] is False
    assert 'HUBSPOT_ACCESS_TOKEN' in data['hubspot']['missing']


def test_hubspot_export_requires_token(monkeypatch) -> None:
    monkeypatch.delenv('HUBSPOT_ACCESS_TOKEN', raising=False)
    monkeypatch.delenv('HUBSPOT_SERVICE_KEY', raising=False)
    monkeypatch.delenv('HUBSPOT_PRIVATE_APP_TOKEN', raising=False)
    monkeypatch.delenv('HUBSPOT_API_KEY', raising=False)
    response = client.post('/api/hubspot-export', json={'lead': {'email': 'demo@example.com', 'name': 'Demo Co'}})
    assert response.status_code == 503
    assert response.json()['ok'] is False


def test_hubspot_export_accepts_valid_lead(monkeypatch) -> None:
    monkeypatch.setenv('HUBSPOT_ACCESS_TOKEN', 'test-token')

    def fake_upsert(_: str, properties: dict[str, str]) -> dict[str, str]:
        assert properties['email'] == 'demo@example.com'
        assert properties['company'] == 'Demo Co'
        return {'id': '12345', 'action': 'created'}

    monkeypatch.setattr(hubspot_service, 'upsert_hubspot_contact', fake_upsert)
    response = client.post('/api/hubspot-export', json={'lead': {'email': 'demo@example.com', 'name': 'Demo Co'}})
    assert response.status_code == 200
    body = response.json()
    assert body['ok'] is True
    assert body['hubspot']['id'] == '12345'
    assert body['hubspot']['action'] == 'created'


def test_hubspot_status_accepts_service_key_alias(monkeypatch) -> None:
    monkeypatch.delenv('HUBSPOT_ACCESS_TOKEN', raising=False)
    monkeypatch.setenv('HUBSPOT_SERVICE_KEY', 'test-service-key')
    monkeypatch.delenv('HUBSPOT_PRIVATE_APP_TOKEN', raising=False)
    monkeypatch.delenv('HUBSPOT_API_KEY', raising=False)
    response = client.get('/api/hubspot-status')
    assert response.status_code == 200
    data = response.json()['hubspot']
    assert data['configured'] is True
    assert data['configuredBy'] == 'HUBSPOT_SERVICE_KEY'


def test_tracking_allowed_origins_supports_comma_list(monkeypatch) -> None:
    monkeypatch.setenv(
        'TRACKING_ALLOWED_ORIGIN',
        'https://nexus-b2b-lead-generation.onrender.com, http://localhost:5173',
    )
    assert config.tracking_allowed_origins() == [
        'https://nexus-b2b-lead-generation.onrender.com',
        'http://localhost:5173',
    ]


def test_schema_includes_tracking_events_table() -> None:
    schema = SCHEMA_PATH.read_text(encoding='utf-8')
    assert 'CREATE TABLE IF NOT EXISTS tracking_events' in schema
    assert 'metadata JSONB' in schema


def test_schema_includes_lead_crud_columns() -> None:
    schema = SCHEMA_PATH.read_text(encoding='utf-8')
    assert 'ALTER TABLE leads ADD COLUMN IF NOT EXISTS intent TEXT' in schema
    assert 'ALTER TABLE leads ADD COLUMN IF NOT EXISTS location TEXT' in schema
    assert 'ALTER TABLE leads ADD COLUMN IF NOT EXISTS budget TEXT' in schema
    assert 'ALTER TABLE leads ADD COLUMN IF NOT EXISTS notes TEXT' in schema


def test_leads_router_is_registered() -> None:
    paths = client.get('/openapi.json').json()['paths']
    assert '/leads/' in paths
    assert 'post' in paths['/leads/']
    assert 'get' in paths['/leads/']


def test_leads_requires_database_url(monkeypatch) -> None:
    monkeypatch.delenv('DATABASE_URL', raising=False)
    response = client.get('/leads/')
    assert response.status_code == 503


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
