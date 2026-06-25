import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SAMPLE_LEADS = [
    {
        "id": "abc123",
        "company": "Acme Corp",
        "contact_name": "Alice Johnson (VP of Sales)",
        "email": "alice.johnson@acmecorp.com",
        "phone": "+1-555-100-0200",
        "website": "https://www.acmecorp.com",
        "industry": "Technology",
        "location": "United States",
        "score": 95,
    }
]


def test_notify_sends_email():
    with patch("app.email.resend") as mock_resend, \
         patch.dict("os.environ", {"RESEND_API_KEY": "re_test_key"}):
        mock_resend.Emails.send.return_value = {"id": "msg_abc123"}

        response = client.post(
            "/api/leads/notify",
            json={"to": "user@example.com", "query": "Acme Corp", "leads": SAMPLE_LEADS},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["message_id"] == "msg_abc123"
    assert data["recipient"] == "user@example.com"


def test_notify_missing_api_key():
    with patch.dict("os.environ", {}, clear=True):
        import os
        os.environ.pop("RESEND_API_KEY", None)

        response = client.post(
            "/api/leads/notify",
            json={"to": "user@example.com", "query": "Acme", "leads": SAMPLE_LEADS},
        )

    assert response.status_code == 503
    assert "RESEND_API_KEY" in response.json()["detail"]


def test_notify_resend_error():
    with patch("app.email.resend") as mock_resend, \
         patch.dict("os.environ", {"RESEND_API_KEY": "re_test_key"}):
        mock_resend.Emails.send.side_effect = Exception("rate limit exceeded")

        response = client.post(
            "/api/leads/notify",
            json={"to": "user@example.com", "query": "Acme", "leads": SAMPLE_LEADS},
        )

    assert response.status_code == 502
    assert "rate limit exceeded" in response.json()["detail"]
