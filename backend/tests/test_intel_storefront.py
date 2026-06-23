"""Tests for NEXUS AI Intelligence enrichment + per-lead storefront."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cloud-saas-hub.preview.emergentagent.com").rstrip("/")

ADMIN_EMAIL = "admin@nexus.io"
ADMIN_PASSWORD = "nexus123"


# ---------------------------- fixtures ----------------------------
@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="session")
def new_user_session():
    """Fresh non-admin user with 0 credits."""
    email = f"TEST_buyer_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "Test123!Pass"
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/register",
               json={"email": email, "password": pwd, "name": "TEST User"}, timeout=30)
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    # Some apps auto-login at register; ensure session has token
    r2 = s.post(f"{BASE_URL}/api/auth/login",
                json={"email": email, "password": pwd}, timeout=30)
    assert r2.status_code == 200, f"new user login: {r2.text}"
    data = r2.json()
    tok = data.get("access_token") or data.get("token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    s._email = email
    return s


# ---------------------------- admin login ----------------------------
class TestAdminLogin:
    def test_login_and_me(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/auth/me", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data.get("role") == "admin"
        assert data.get("email") == ADMIN_EMAIL


# ---------------------------- process-leads (admin only) ----------------------------
class TestProcessLeads:
    @pytest.fixture(scope="class")
    def enriched(self, admin_session):
        body = {
            "ai_model": "llama",
            "leads": [
                {"company": "Stripe", "website": "https://stripe.com",
                 "email": "press@stripe.com", "phone": "+1-415-555-0199",
                 "city": "San Francisco", "state": "CA", "category": "fintech",
                 "full_name": "Pat Doe"},
                {"company": "ShadyCo", "website": "",
                 "email": "abc@mailinator.com", "phone": "",
                 "city": "", "state": "", "category": "unknown",
                 "full_name": "Anon"},
            ]
        }
        r = admin_session.post(f"{BASE_URL}/api/enrichment/process-leads",
                               json=body, timeout=180)
        assert r.status_code == 200, f"process-leads failed: {r.status_code} {r.text}"
        return r.json()

    def test_response_shape(self, enriched):
        assert enriched["processed"] == 2
        assert "leads" in enriched and len(enriched["leads"]) == 2
        assert "llama" in enriched["model"].lower() or "Llama" in enriched["model"]

    def test_per_lead_intel_payload(self, enriched):
        for ld in enriched["leads"]:
            assert isinstance(ld.get("data_confidence_score"), (int, float))
            assert 0 <= ld["data_confidence_score"] <= 100
            assert isinstance(ld.get("cross_verification"), list)
            assert isinstance(ld.get("risk_matrix"), list)
            assert ld.get("operational_value_tier") in ("Strategic", "Tactical", "Operational")
            assert isinstance(ld.get("price_per_lead"), int)
            assert ld.get("price_per_lead") >= 1
            assert "ready_to_sell" in ld

    def test_weak_lead_flagged(self, enriched):
        weak = enriched["leads"][1]
        flags = [str(r.get("flag", "")).lower() for r in weak.get("risk_matrix", [])]
        # Expect at least one risk flag (e.g. disposable email)
        assert weak["risk_matrix"], f"Weak lead has no risk_matrix: {weak}"
        # Disposable email should appear
        assert any("disposable" in f or "mailinator" in f for f in flags) or weak["data_confidence_score"] < 50

    def test_strong_lead_higher_confidence(self, enriched):
        strong = enriched["leads"][0]
        weak = enriched["leads"][1]
        assert strong["data_confidence_score"] >= weak["data_confidence_score"]

    def test_non_admin_403(self, new_user_session):
        r = new_user_session.post(f"{BASE_URL}/api/enrichment/process-leads",
                                  json={"leads": [{"company": "X"}], "ai_model": "llama"},
                                  timeout=30)
        assert r.status_code == 403, f"expected 403, got {r.status_code} {r.text}"


# ---------------------------- storefront browse ----------------------------
class TestStorefrontBrowse:
    def test_browse_returns_available_masked(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/storefront/leads?limit=20", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "leads" in data and "filters" in data
        assert "industries" in data["filters"]
        assert "states" in data["filters"]
        assert "tiers" in data["filters"]
        assert data["filters"]["tiers"] == ["Strategic", "Tactical", "Operational"]
        # If there are leads, ensure they're masked + carry intel metrics
        for ld in data["leads"][:5]:
            assert ld.get("locked") is True
            assert ld.get("purchase_status") == "available"
            assert "company_masked" in ld
            assert "contact_masked" in ld
            assert "email" not in ld
            assert "phone" not in ld
            assert "data_confidence_score" in ld
            assert "cross_verification" in ld
            assert "risk_matrix" in ld
            assert ld.get("operational_value_tier") in ("Strategic", "Tactical", "Operational")
            assert isinstance(ld.get("price_per_lead"), int)

    def test_filter_min_confidence(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/storefront/leads?min_confidence=70&limit=50", timeout=30)
        assert r.status_code == 200
        for ld in r.json()["leads"]:
            assert ld["data_confidence_score"] >= 70

    def test_filter_tier(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/storefront/leads?tier=Strategic&limit=50", timeout=30)
        assert r.status_code == 200
        for ld in r.json()["leads"]:
            assert ld["operational_value_tier"] == "Strategic"

    def test_filter_state(self, admin_session):
        # Discover a state first
        r0 = admin_session.get(f"{BASE_URL}/api/storefront/leads?limit=200", timeout=30).json()
        states = r0["filters"]["states"]
        if not states:
            pytest.skip("No states available to filter")
        st = states[0]
        r = admin_session.get(f"{BASE_URL}/api/storefront/leads?state={st}&limit=50", timeout=30)
        assert r.status_code == 200
        for ld in r.json()["leads"]:
            assert (ld.get("state") or "").lower() == st.lower()


# ---------------------------- purchase flows ----------------------------
class TestPurchaseFlow:
    @pytest.fixture(scope="class")
    def available_lead_id(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/storefront/leads?limit=50", timeout=30)
        assert r.status_code == 200
        leads = r.json()["leads"]
        assert leads, "No available leads in storefront to purchase"
        return leads[0]["id"]

    def test_admin_purchase_unlocks_full(self, admin_session, available_lead_id):
        r = admin_session.post(f"{BASE_URL}/api/storefront/purchase-leads",
                               json={"lead_ids": [available_lead_id]}, timeout=60)
        assert r.status_code == 200, f"purchase failed: {r.status_code} {r.text}"
        data = r.json()
        assert data["purchased"] == 1
        assert "charged_credits" in data
        assert len(data["leads"]) == 1
        ld = data["leads"][0]
        # Full unlocked payload
        assert "email" in ld
        assert "phone" in ld
        assert "company" in ld
        assert ld.get("id") == available_lead_id
        # Stash for double-sell test
        TestPurchaseFlow._sold_id = available_lead_id

    def test_purchased_lead_disappears_from_storefront(self, admin_session):
        sold = TestPurchaseFlow._sold_id
        r = admin_session.get(f"{BASE_URL}/api/storefront/leads?limit=200", timeout=30)
        ids = [l["id"] for l in r.json()["leads"]]
        assert sold not in ids, "Sold lead still appears in storefront"

    def test_double_sell_blocked(self, admin_session):
        sold = TestPurchaseFlow._sold_id
        r = admin_session.post(f"{BASE_URL}/api/storefront/purchase-leads",
                               json={"lead_ids": [sold]}, timeout=30)
        assert r.status_code == 400
        assert "available" in r.text.lower()

    def test_insufficient_credits_for_new_user(self, admin_session, new_user_session):
        # Grab another available lead
        r = admin_session.get(f"{BASE_URL}/api/storefront/leads?limit=10", timeout=30)
        leads = r.json()["leads"]
        if not leads:
            pytest.skip("No more available leads")
        lead_id = leads[0]["id"]
        r2 = new_user_session.post(f"{BASE_URL}/api/storefront/purchase-leads",
                                   json={"lead_ids": [lead_id]}, timeout=30)
        assert r2.status_code == 402, f"expected 402, got {r2.status_code} {r2.text}"
        assert "insufficient" in r2.text.lower()
        # Verify still available
        r3 = admin_session.get(f"{BASE_URL}/api/storefront/leads?limit=200", timeout=30)
        ids = [l["id"] for l in r3.json()["leads"]]
        assert lead_id in ids, "Lead was wrongly marked sold despite 402"
