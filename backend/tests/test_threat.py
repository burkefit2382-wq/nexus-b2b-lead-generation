"""NEXUS Threat Intel endpoints — RBAC, scan, reports, outreach profile."""
import os
import uuid
import pytest
import requests

BASE = (os.environ.get("REACT_APP_BACKEND_URL")
        or "https://cloud-saas-hub.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

ADMIN_EMAIL = "admin@nexus.io"
ADMIN_PASS = "nexus123"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=20)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def user_session():
    email = f"test_threat_{uuid.uuid4().hex[:8]}@example.com"
    s = requests.Session()
    r = s.post(f"{API}/auth/register",
               json={"email": email, "password": "Passw0rd!", "name": "ThreatTester"},
               timeout=20)
    assert r.status_code == 200, r.text
    return s


# ---------------- RBAC: non-admin must get 403 ----------------
def test_threat_scan_forbidden_for_user(user_session):
    r = user_session.post(f"{API}/threat/scan", json={"domain": "example.com"}, timeout=15)
    assert r.status_code == 403, r.text


def test_threat_reports_forbidden_for_user(user_session):
    r = user_session.get(f"{API}/threat/reports", timeout=15)
    assert r.status_code == 403, r.text


def test_threat_outreach_profile_get_forbidden_for_user(user_session):
    r = user_session.get(f"{API}/threat/outreach-profile", timeout=15)
    assert r.status_code == 403, r.text


def test_threat_outreach_profile_put_forbidden_for_user(user_session):
    r = user_session.put(f"{API}/threat/outreach-profile",
                         json={"sender_name": "x", "brand": "y", "services": "z", "cta": ""},
                         timeout=15)
    assert r.status_code == 403, r.text


# ---------------- Outreach profile: admin GET/PUT persistence ----------------
def test_outreach_profile_put_and_get_persists(admin_session):
    payload = {
        "sender_name": "TEST_Sender",
        "sender_email": "",
        "brand": "TEST_Brand",
        "services": "pentest, breach response",
        "cta": "https://test.example/book",
        "provider": "",
        "auto_send": False,
    }
    r = admin_session.put(f"{API}/threat/outreach-profile", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("updated") is True
    assert body["sender_name"] == "TEST_Sender"
    assert body["brand"] == "TEST_Brand"

    # GET to verify persistence
    g = admin_session.get(f"{API}/threat/outreach-profile", timeout=10)
    assert g.status_code == 200
    p = g.json()
    assert p.get("sender_name") == "TEST_Sender"
    assert p.get("brand") == "TEST_Brand"
    assert p.get("services") == "pentest, breach response"
    assert "_id" not in p


# ---------------- Scan low-risk ----------------
def test_threat_scan_low_risk_example_com(admin_session):
    r = admin_session.post(f"{API}/threat/scan",
                           json={"domain": "example.com", "model": "deepseek"},
                           timeout=90)
    assert r.status_code == 200, r.text
    rep = r.json()
    assert "id" in rep
    assert rep["domain"] == "example.com"
    assert isinstance(rep["risk_score"], (int, float))
    assert 0 <= rep["risk_score"] <= 10
    assert "findings" in rep and isinstance(rep["findings"], list)
    # low risk -> no email draft, high_ticket False
    if rep["risk_score"] <= 5:
        assert rep["high_ticket"] is False
        assert rep.get("email_draft") in (None, {})


# ---------------- Scan high-risk ----------------
def test_threat_scan_high_risk_neverssl(admin_session):
    r = admin_session.post(f"{API}/threat/scan",
                           json={"domain": "neverssl.com", "model": "deepseek"},
                           timeout=120)
    assert r.status_code == 200, r.text
    rep = r.json()
    assert rep["domain"] == "neverssl.com"
    assert isinstance(rep["risk_score"], (int, float))
    assert 0 <= rep["risk_score"] <= 10
    # Should be high
    assert rep["risk_score"] > 5, f"expected >5, got {rep['risk_score']}"
    assert rep["high_ticket"] is True
    draft = rep.get("email_draft")
    assert isinstance(draft, dict) and draft, "email_draft missing for high-ticket"
    assert draft.get("subject")
    assert draft.get("body")


# ---------------- Reports list ----------------
def test_threat_reports_list_admin(admin_session):
    r = admin_session.get(f"{API}/threat/reports", timeout=15)
    assert r.status_code == 200
    arr = r.json()
    assert isinstance(arr, list)
    for item in arr:
        assert "_id" not in item
        assert "id" in item
        assert "domain" in item
        assert "risk_score" in item


def test_threat_reports_high_ticket_filter(admin_session):
    r = admin_session.get(f"{API}/threat/reports",
                          params={"high_ticket_only": "true"}, timeout=15)
    assert r.status_code == 200
    arr = r.json()
    for item in arr:
        assert item.get("high_ticket") is True
        assert item.get("risk_score", 0) > 5
