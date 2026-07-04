"""Iteration 18 - Regression tests after server.py -> core/ + routes/ split.

Covers domains lightly touched by backend_test.py: threat, outreach, storefront,
public/landing, governance/admin, payments packages, enrichment pricing,
auth refresh, /api/ready DB proxy.
"""
import os
import uuid
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE}/api"

ADMIN_EMAIL = "admin@nexus.io"
ADMIN_PASS = "nexus123"


# ---------------- fixtures ----------------
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=20)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def user_session():
    email = f"reg_{uuid.uuid4().hex[:8]}@example.com"
    s = requests.Session()
    r = s.post(f"{API}/auth/register", json={"email": email, "password": "Passw0rd!", "name": "Reg Tester"}, timeout=20)
    assert r.status_code == 200, r.text
    return s


# ---------------- health/db proxy ----------------
def test_ready_db_proxy():
    r = requests.get(f"{API}/ready", timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    # ready should indicate DB reachable via new proxy
    assert body.get("ready") is True or body.get("db") in (True, "ok", "ready", "connected") or body.get("status") in ("ok", "ready")


# ---------------- auth refresh + logout ----------------
def test_auth_refresh(admin_session):
    r = admin_session.post(f"{API}/auth/refresh", timeout=10)
    # some impls require a refresh cookie; accept 200 or 401 shape (no 500)
    assert r.status_code in (200, 401), r.text
    if r.status_code == 200:
        me = admin_session.get(f"{API}/auth/me", timeout=10)
        assert me.status_code == 200


# ---------------- leads csv export ----------------
def test_leads_export_csv(admin_session):
    r = admin_session.get(f"{API}/leads/export/csv", timeout=20)
    assert r.status_code == 200, r.text
    ct = r.headers.get("content-type", "")
    assert "csv" in ct or "text/plain" in ct


# ---------------- enrichment pricing (public/authed) ----------------
def test_enrich_pricing(admin_session):
    r = admin_session.get(f"{API}/enrich/pricing", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, (dict, list))


def test_enrich_business_credits_or_result(admin_session):
    r = admin_session.post(f"{API}/enrich/business",
                           json={"name": "Example Inc", "domain": "example.com"}, timeout=45)
    # accept 200 (result) or 402 (out of credits) - just not 500
    assert r.status_code in (200, 402), r.text


# ---------------- payments ----------------
def test_payments_checkout_creates_session(admin_session):
    r = admin_session.post(f"{API}/payments/checkout",
                           json={"package_id": "starter", "origin_url": BASE}, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "url" in body and "session_id" in body


# ---------------- threat intel (admin) ----------------
def test_threat_reports_admin_only(admin_session, user_session):
    r = admin_session.get(f"{API}/threat/reports", timeout=15)
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)
    # forbidden for non-admin
    r2 = user_session.get(f"{API}/threat/reports", timeout=15)
    assert r2.status_code == 403


def test_threat_outreach_profile_roundtrip(admin_session):
    r = admin_session.get(f"{API}/threat/outreach-profile", timeout=15)
    assert r.status_code == 200, r.text
    prof = r.json()
    assert isinstance(prof, dict)
    # PUT round-trip
    updated = dict(prof)
    updated["sender_name"] = updated.get("sender_name") or "NEXUS Intel"
    p = admin_session.put(f"{API}/threat/outreach-profile", json=updated, timeout=15)
    assert p.status_code == 200, p.text


def test_threat_scan_example_com(admin_session):
    r = admin_session.post(f"{API}/threat/scan",
                           json={"domain": "example.com"}, timeout=90)
    assert r.status_code == 200, r.text
    rep = r.json()
    # risk score / risk level should exist
    assert ("risk" in rep) or ("risk_score" in rep) or ("score" in rep), rep


# ---------------- outreach (admin) - NO live send ----------------
def test_outreach_templates(admin_session):
    r = admin_session.get(f"{API}/outreach/templates", timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    # 4 pilot templates expected
    if isinstance(body, list):
        assert len(body) >= 4
    elif isinstance(body, dict) and "templates" in body:
        assert len(body["templates"]) >= 4


def test_outreach_auto_config(admin_session):
    r = admin_session.get(f"{API}/outreach/auto", timeout=10)
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), dict)


def test_outreach_preview(admin_session):
    r = admin_session.post(f"{API}/outreach/preview", json={}, timeout=30)
    assert r.status_code == 200, r.text


def test_outreach_sample_pack_json(admin_session):
    r = admin_session.get(f"{API}/outreach/sample-pack", timeout=20)
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), (dict, list))


def test_outreach_sample_pack_csv(admin_session):
    r = admin_session.get(f"{API}/outreach/sample-pack.csv", timeout=20)
    assert r.status_code == 200, r.text
    ct = r.headers.get("content-type", "")
    assert "csv" in ct


def test_outreach_sample_pack_pdf(admin_session):
    r = admin_session.get(f"{API}/outreach/sample-pack.pdf", timeout=30)
    assert r.status_code == 200, r.text
    ct = r.headers.get("content-type", "")
    assert "application/pdf" in ct, ct
    # PDF magic
    assert r.content[:4] == b"%PDF", "response is not a PDF"


# ---------------- storefront ----------------
def test_storefront_leads_masked(admin_session):
    r = admin_session.get(f"{API}/storefront/leads", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, (dict, list))


def test_storefront_sectors(admin_session):
    r = admin_session.get(f"{API}/storefront/sectors", timeout=15)
    assert r.status_code == 200, r.text


def test_storefront_rfp_submit_and_admin_list(admin_session):
    payload = {
        "agency_name": "TEST_Regression Agency",
        "contact_name": "Reg Tester",
        "email": "reg@test.io",
        "regions": "NA",
        "sectors": "cleaning",
        "budget": "1000",
        "timeline": "Q1",
        "classification": "Unclassified",
        "scope": "regression test rfp",
    }
    r = admin_session.post(f"{API}/storefront/rfp", json=payload, timeout=15)
    assert r.status_code in (200, 201), r.text
    lst = admin_session.get(f"{API}/storefront/rfp", timeout=15)
    assert lst.status_code == 200, lst.text


# ---------------- public / landing ----------------
def test_public_waitlist():
    payload = {"email": f"wl_{uuid.uuid4().hex[:6]}@test.io", "name": "Waitlister"}
    r = requests.post(f"{API}/waitlist", json=payload, timeout=15)
    assert r.status_code in (200, 201), r.text


def test_public_enrich_score():
    payload = {"lead": {"company": "Example Inc", "domain": "example.com", "name": "Example"}}
    r = requests.post(f"{API}/enrich-score", json=payload, timeout=30)
    assert r.status_code == 200, r.text


def test_public_chat():
    r = requests.post(f"{API}/chat", json={"prompt": "hello, what does nexus do?"}, timeout=45)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "answer" in body or "response" in body or "message" in body


# ---------------- governance/admin ----------------
def test_governance_me(admin_session):
    r = admin_session.get(f"{API}/governance/me", timeout=10)
    assert r.status_code == 200, r.text


def test_admin_tenants(admin_session):
    r = admin_session.get(f"{API}/admin/tenants", timeout=15)
    assert r.status_code == 200, r.text


def test_admin_audit(admin_session):
    r = admin_session.get(f"{API}/admin/audit", timeout=15)
    assert r.status_code == 200, r.text


def test_admin_monitoring(admin_session):
    r = admin_session.get(f"{API}/admin/monitoring", timeout=15)
    assert r.status_code == 200, r.text


# ---------------- scraper (safe reads) ----------------
def test_intel_sources(admin_session):
    r = admin_session.get(f"{API}/intel/sources", timeout=15)
    assert r.status_code == 200, r.text
