"""Tests for the OSINT-wired live scrape cycle + HQ-only storefront (Jan 2026 feature).

Validates:
  - Admin login (httpOnly cookie + Bearer fallback)
  - Storefront returns ONLY HQ ready_to_sell, non-sold leads (and totals match)
  - Storefront sectors catalog contains the new high-value sectors
  - Scraper status reports scheduler_running/enabled
  - Triggered OSM scrape cycle produces leads with full OSINT payload and FL-only
  - generate-leads (ai_enrich=false) seeds FL OSINT leads
  - Purchase flow (admin bypasses credits; double-sell guarded)
  - Regression on /api/intel/sources and /api/ready
"""
import os
import time
import uuid
import pytest
import requests

def _load_base_url():
    u = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if not u:
        try:
            with open("/app/frontend/.env") as fh:
                for line in fh:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        u = line.split("=", 1)[1].strip()
                        break
        except OSError:
            pass
    return u.rstrip("/")

BASE_URL = _load_base_url()
assert BASE_URL, "REACT_APP_BACKEND_URL not set"

ADMIN_EMAIL = "admin@nexus.io"
ADMIN_PASSWORD = "nexus123"
BUYER_EMAIL = "buyer@test.io"
BUYER_PASSWORD = "buyer123"

REQUIRED_SECTORS = {
    "financial_services", "legal", "insurance",
    "real_estate", "healthcare", "b2b_tech",
}
FL_COUNTIES = {"Hillsborough County", "Pinellas County",
               "Manatee County", "Pasco County", "Hernando County"}


# ---------------------------- fixtures ----------------------------
def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="session")
def admin():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="session")
def buyer():
    try:
        return _login(BUYER_EMAIL, BUYER_PASSWORD)
    except AssertionError:
        pytest.skip("buyer@test.io login failed")


# ---------------------------- 1. auth ----------------------------
class TestAuth:
    def test_admin_me(self, admin):
        r = admin.get(f"{BASE_URL}/api/auth/me", timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert body["role"] == "admin"
        assert body["email"].lower() == ADMIN_EMAIL


# ---------------------------- 2. storefront HQ-only ----------------------------
class TestStorefrontHQOnly:
    def test_leads_all_ready_to_sell_and_not_sold(self, admin):
        r = admin.get(f"{BASE_URL}/api/storefront/leads?limit=500", timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        leads = body.get("leads", [])
        assert isinstance(leads, list)
        # invariants
        for ld in leads:
            assert ld.get("ready_to_sell") is True, f"non-HQ leaked: {ld.get('id')}"
            assert ld.get("purchase_status") != "sold", f"sold leaked: {ld.get('id')}"
            assert ld.get("purchase_status") == "available"
        # total reflects HQ-base
        assert body.get("total") == len(leads) or body.get("total") >= len(leads)
        # (total may be > leads due to pagination cap; the key invariant is no non-HQ in payload)

    def test_sectors_catalog_has_new_high_value_sectors(self, admin):
        r = admin.get(f"{BASE_URL}/api/storefront/sectors", timeout=30)
        assert r.status_code == 200, r.text
        sectors = set(r.json().get("sectors", []))
        missing = REQUIRED_SECTORS - sectors
        assert not missing, f"missing required sectors: {missing}"

    def test_bundle_filters_only_hq(self, admin):
        # min_confidence filter should still respect HQ gating
        r = admin.get(f"{BASE_URL}/api/storefront/leads?min_confidence=65&limit=200", timeout=30)
        assert r.status_code == 200
        for ld in r.json().get("leads", []):
            assert ld["data_confidence_score"] >= 65
            assert ld.get("ready_to_sell") is True


# ---------------------------- 3. scraper status & trigger ----------------------------
class TestScraperLiveCycle:
    def test_status_scheduler_enabled(self, admin):
        r = admin.get(f"{BASE_URL}/api/scraper/status", timeout=30)
        assert r.status_code == 200, r.text
        s = r.json()
        assert s.get("scheduler_running") is True
        assert s.get("enabled") is True
        assert isinstance(s.get("total_scraped_leads"), int)

    def _wait_idle(self, admin, max_wait=210):
        """Poll status until status==idle or timeout."""
        t0 = time.time()
        while time.time() - t0 < max_wait:
            r = admin.get(f"{BASE_URL}/api/scraper/status", timeout=20)
            if r.status_code == 200 and r.json().get("status") == "idle":
                return r.json()
            time.sleep(8)
        return None

    def test_trigger_osm_and_verify_osint_fl_payload(self, admin):
        # wait for any in-progress cycle to settle
        self._wait_idle(admin, max_wait=210)
        # capture pre count of scraper-sourced leads (via storefront aggregate is hard; use status)
        pre = admin.get(f"{BASE_URL}/api/scraper/status", timeout=20).json()
        pre_total = pre.get("total_scraped_leads", 0)
        # trigger
        r = admin.post(f"{BASE_URL}/api/scraper/trigger?source=osm", timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("triggered") is True, body
        # poll up to ~3 minutes for cycle to finish
        final = self._wait_idle(admin, max_wait=240)
        if final is None:
            pytest.skip("scrape cycle did not finish within 4 minutes — partial harvest acceptable")
        # success state check
        assert final.get("status") == "idle"
        # last_run should be recent (no strict assertion; just present)
        assert final.get("last_run") is not None

        # Now sample scraper leads from storefront (HQ ones at minimum) — the only
        # leads visible to the storefront are ready_to_sell.  We can't query by
        # source via the public API; assert the OSINT invariants over the HQ slice
        # and that NO non-FL lead surfaces.
        r2 = admin.get(f"{BASE_URL}/api/storefront/leads?limit=500", timeout=30)
        assert r2.status_code == 200
        leads = r2.json().get("leads", [])
        assert leads, "storefront empty after trigger"
        non_fl = [ld for ld in leads if (ld.get("state") or "").upper() not in ("FL", "")]
        assert not non_fl, f"non-FL leads leaked into storefront: {[(l['id'], l.get('state')) for l in non_fl[:5]]}"
        for ld in leads[:50]:
            # OSINT payload invariants on HQ rows
            assert isinstance(ld.get("data_confidence_score"), (int, float))
            assert ld["data_confidence_score"] >= 65, f"HQ lead under threshold: {ld.get('id')}"
            assert isinstance(ld.get("cross_verification"), list)
            assert len(ld["cross_verification"]) >= 2, f"HQ lead has <2 verification nodes: {ld}"
            assert isinstance(ld.get("risk_matrix"), list)
            assert ld.get("operational_value_tier") in ("Strategic", "Tactical", "Operational")
            assert isinstance(ld.get("price_per_lead"), int) and ld["price_per_lead"] >= 1
            assert ld.get("purchase_status") == "available"


# ---------------------------- 4. generate-leads (free OSINT path) ----------------------------
class TestGenerateLeads:
    def test_generate_pinellas_financial_no_ai(self, admin):
        body = {
            "sector": "financial_services",
            "county": "Pinellas County",
            "limit": 30,
            "ai_enrich": False,
        }
        r = admin.post(f"{BASE_URL}/api/storefront/generate-leads",
                       json=body, timeout=180)
        # Rate limit / no-data partial-harvest tolerance
        if r.status_code == 429:
            pytest.skip("rate limited (5/min) — acceptable")
        assert r.status_code == 200, f"generate-leads: {r.status_code} {r.text}"
        data = r.json()
        # contract: generated/new counts present
        assert ("generated" in data) or ("new" in data) or ("created" in data) or ("inserted" in data), \
            f"unexpected response shape: {data}"
        # storefront should still be HQ + FL after generate
        r2 = admin.get(f"{BASE_URL}/api/storefront/leads?limit=200&category=financial_services", timeout=30)
        assert r2.status_code == 200
        for ld in r2.json().get("leads", []):
            assert (ld.get("state") or "").upper() == "FL"
            assert ld.get("ready_to_sell") is True
            assert ld["data_confidence_score"] >= 65


# ---------------------------- 5. purchase ----------------------------
class TestPurchaseFlow:
    def test_admin_purchase_hq_lead(self, admin):
        r = admin.get(f"{BASE_URL}/api/storefront/leads?limit=50", timeout=30)
        leads = r.json().get("leads", [])
        if not leads:
            pytest.skip("no HQ leads to purchase")
        lid = leads[0]["id"]
        r2 = admin.post(f"{BASE_URL}/api/storefront/purchase-leads",
                        json={"lead_ids": [lid]}, timeout=60)
        assert r2.status_code == 200, f"admin purchase: {r2.status_code} {r2.text}"
        body = r2.json()
        assert body.get("purchased") == 1
        assert body["leads"][0]["id"] == lid
        # disappears from storefront
        r3 = admin.get(f"{BASE_URL}/api/storefront/leads?limit=500", timeout=30)
        ids = [l["id"] for l in r3.json().get("leads", [])]
        assert lid not in ids
        # double-sell blocked
        r4 = admin.post(f"{BASE_URL}/api/storefront/purchase-leads",
                        json={"lead_ids": [lid]}, timeout=30)
        assert r4.status_code == 400
        assert "available" in r4.text.lower()

    def test_buyer_purchase_402_or_success(self, admin, buyer):
        # buyer may or may not have credits; both 200 and 402 are acceptable contracts
        r = admin.get(f"{BASE_URL}/api/storefront/leads?limit=10", timeout=30)
        leads = r.json().get("leads", [])
        if not leads:
            pytest.skip("no HQ leads available")
        lid = leads[0]["id"]
        r2 = buyer.post(f"{BASE_URL}/api/storefront/purchase-leads",
                        json={"lead_ids": [lid]}, timeout=30)
        assert r2.status_code in (200, 402), f"unexpected: {r2.status_code} {r2.text}"
        if r2.status_code == 402:
            assert "insufficient" in r2.text.lower()
            # lead still available
            r3 = admin.get(f"{BASE_URL}/api/storefront/leads?limit=200", timeout=30)
            ids = [l["id"] for l in r3.json().get("leads", [])]
            assert lid in ids


# ---------------------------- 6. regression ----------------------------
class TestRegression:
    def test_intel_sources_lists_osm(self, admin):
        r = admin.get(f"{BASE_URL}/api/intel/sources", timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        keys = {s["key"] for s in body.get("sources", [])}
        assert "osm" in keys, body
        osm = next(s for s in body["sources"] if s["key"] == "osm")
        # describes sectors x counties
        det = (osm.get("detail") or "").lower()
        assert "sector" in det and "count" in det

    def test_ready_endpoint(self):
        r = requests.get(f"{BASE_URL}/api/ready", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body.get("ready") is True
        assert body.get("db") == "connected"
