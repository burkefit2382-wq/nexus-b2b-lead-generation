from fastapi.testclient import TestClient

try:
    from backend.app.api import membership as membership_api
    from backend.app.core.db import get_db
    from backend.app.main import app
except ModuleNotFoundError:
    from app.api import membership as membership_api
    from app.core.db import get_db
    from app.main import app

client = TestClient(app)


def _override_db():
    return object()


def test_membership_webhook_rejects_bad_signature(monkeypatch) -> None:
    app.dependency_overrides[get_db] = _override_db

    def fake_construct_webhook_event(_: bytes, __: str):
        raise membership_api.stripe.SignatureVerificationError('bad signature', 'test-sig')

    monkeypatch.setattr(membership_api.stripe_service, 'construct_webhook_event', fake_construct_webhook_event)
    response = client.post('/api/membership/webhook', content=b'{}', headers={'stripe-signature': 'test-sig'})
    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()['detail'] == 'Invalid webhook signature.'


def test_membership_webhook_routes_checkout_completed(monkeypatch) -> None:
    app.dependency_overrides[get_db] = _override_db
    called = {'checkout': False}

    monkeypatch.setattr(
        membership_api.stripe_service,
        'construct_webhook_event',
        lambda *_: {'type': 'checkout.session.completed', 'data': {'object': {'customer_email': 'demo@example.com'}}},
    )

    def fake_handle_checkout_completed(*_):
        called['checkout'] = True

    monkeypatch.setattr(membership_api, '_handle_checkout_completed', fake_handle_checkout_completed)
    response = client.post('/api/membership/webhook', content=b'{}', headers={'stripe-signature': 'test-sig'})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()['received'] == 'ok'
    assert called['checkout'] is True


def test_membership_webhook_routes_subscription_updated(monkeypatch) -> None:
    app.dependency_overrides[get_db] = _override_db
    called = {'subscription': False}

    monkeypatch.setattr(
        membership_api.stripe_service,
        'construct_webhook_event',
        lambda *_: {
            'type': 'customer.subscription.updated',
            'data': {'object': {'id': 'sub_123', 'status': 'active'}},
        },
    )

    def fake_handle_subscription_change(*_):
        called['subscription'] = True

    monkeypatch.setattr(membership_api, '_handle_subscription_change', fake_handle_subscription_change)
    response = client.post('/api/membership/webhook', content=b'{}', headers={'stripe-signature': 'test-sig'})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()['received'] == 'ok'
    assert called['subscription'] is True
