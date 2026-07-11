from types import SimpleNamespace

try:
    from backend.app import main as app_main
    from backend.app.api import leads as leads_api
    from backend.app.main import app
    from backend.app.schemas.lead import LeadCreate
    from backend.app.services import hubspot as hubspot_service
    from backend.app.services import stripe_service
except ModuleNotFoundError:
    from app import main as app_main
    from app.api import leads as leads_api
    from app.main import app
    from app.schemas.lead import LeadCreate
    from app.services import hubspot as hubspot_service
    from app.services import stripe_service

from fastapi.testclient import TestClient


client = TestClient(app)


def test_healthcheck_reports_healthy_dependencies(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost:5432/neondb?sslmode=require")
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setenv("PRICE_ID", "price_test")
    monkeypatch.setenv("HUBSPOT_PRIVATE_APP_TOKEN", "pat_test")
    monkeypatch.setattr(app_main, "probe_tcp_endpoint", lambda host, port: (True, f"Connected to {host}:{port}."))

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["dependencies"]["database"]["required"] is True
    assert body["dependencies"]["database"]["healthy"] is True
    assert response.headers["X-Request-Id"]


def test_api_health_is_degraded_when_optional_integrations_are_missing(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost:5432/neondb?sslmode=require")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("PRICE_ID", raising=False)
    monkeypatch.delenv("HUBSPOT_PRIVATE_APP_TOKEN", raising=False)
    monkeypatch.delenv("HUBSPOT_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("HUBSPOT_SERVICE_KEY", raising=False)
    monkeypatch.delenv("HUBSPOT_API_KEY", raising=False)
    monkeypatch.setattr(app_main, "probe_tcp_endpoint", lambda host, port: (True, f"Connected to {host}:{port}."))

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["healthz"] == "/healthz"
    assert body["dependencies"]["database"]["healthy"] is True
    assert body["dependencies"]["stripe"]["configured"] is False
    assert body["dependencies"]["hubspot"]["configured"] is False


def test_hubspot_private_app_token_is_authoritative(monkeypatch) -> None:
    monkeypatch.setenv("HUBSPOT_PRIVATE_APP_TOKEN", "pat_test")
    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "legacy-access-token")
    status = hubspot_service.hubspot_status()

    assert status["configured"] is True
    assert status["configuredBy"] == "HUBSPOT_PRIVATE_APP_TOKEN"
    assert status["canonicalTokenName"] == "HUBSPOT_PRIVATE_APP_TOKEN"


def test_create_lead_continues_when_hubspot_sync_fails(monkeypatch) -> None:
    class FakeDB:
        def __init__(self) -> None:
            self.added = []
            self.committed = False
            self.rolled_back = False
            self.refreshed = False

        def add(self, obj) -> None:
            self.added.append(obj)

        def commit(self) -> None:
            self.committed = True

        def rollback(self) -> None:
            self.rolled_back = True

        def refresh(self, obj) -> None:
            self.refreshed = True

    monkeypatch.setattr(leads_api, "hubspot_access_token", lambda: "pat_test")
    monkeypatch.setattr(leads_api, "hubspot_contact_properties", lambda payload: {"email": payload["email"], "company": payload["name"]})

    def fail_upsert(*_args, **_kwargs):
        raise hubspot_service.HubSpotExportError("temporary outage", status=429)

    monkeypatch.setattr(leads_api, "upsert_hubspot_contact", fail_upsert)
    fake_db = FakeDB()

    lead = leads_api.create_lead(LeadCreate(name="Demo Co", email="demo@example.com"), db=fake_db)

    assert lead.email == "demo@example.com"
    assert fake_db.committed is True
    assert fake_db.refreshed is True
    assert fake_db.rolled_back is False


def test_create_checkout_session_passes_idempotency_key(monkeypatch) -> None:
    monkeypatch.setenv("PRICE_ID", "price_123")
    captured: dict[str, object] = {}

    class FakeSessions:
        def create(self, params=None, options=None):
            captured["params"] = params
            captured["options"] = options
            return SimpleNamespace(url="https://checkout.stripe.test/session")

    class FakeClient:
        def __init__(self) -> None:
            self.v1 = SimpleNamespace(checkout=SimpleNamespace(sessions=FakeSessions()))

    monkeypatch.setattr(stripe_service, "_stripe_client", lambda: FakeClient())

    url = stripe_service.create_checkout_session(
        "buyer@example.com",
        "https://app.example.com/success",
        "https://app.example.com/cancel",
        idempotency_key="idem-123",
    )

    assert url == "https://checkout.stripe.test/session"
    assert captured["params"] == {
        "mode": "subscription",
        "customer_email": "buyer@example.com",
        "line_items": [{"price": "price_123", "quantity": 1}],
        "success_url": "https://app.example.com/success",
        "cancel_url": "https://app.example.com/cancel",
    }
    assert captured["options"] == {"idempotency_key": "idem-123"}
