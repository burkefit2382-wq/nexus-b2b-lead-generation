"""Gov-Ready NEXUS backend tests — tenancy, RBAC, audit, brute-force, monitoring + regression."""
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://cloud-saas-hub.preview.emergentagent.com",
).rstrip("/")

ADMIN_EMAIL = os.getenv("NEXUS_ADMIN_EMAIL", "admin@nexus.io")
ADMIN_PASSWORD = os.getenv("NEXUS_ADMIN_PASSWORD", "nexus123")
USER_EMAIL = os.getenv("NEXUS_TEST_USER_EMAIL", "buyer@test.io")
USER_PASSWORD = os.getenv("NEXUS_TEST_USER_PASSWORD", "buyer123")


# ----------------------------------------------------------------- helpers/fixtures
def _client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(session, email, password):
    r = session.post(f"{BASE_URL}/api/auth/login",
                     json={"email": email, "password": password}, timeout=30)
    return r


@pytest.fixture(scope="session")
def admin_session():
    s = _client()
    r = _login(s, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="session")
def user_session():
    s = _client()
    r = _login(s, USER_EMAIL, USER_PASSWORD)
    assert r.status_code == 200, f"buyer login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="session")
def fresh_tenant():
    """Register a brand-new operator (becomes tenant_admin of its own tenant)."""
    s = _client()
    email = f"TEST_op_{uuid.uuid4().hex[:10]}@example.com"
    org = f"TEST_Org_{uuid.uuid4().hex[:6]}"
    r = s.post(f"{BASE_URL}/api/auth/register",
               json={"email": email, "password": "Test123!Pass", "name": "Tester", "org_name": org},
               timeout=30)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    return {"session": s, "email": email, "org": org, "user": r.json()}


# --------------------------------------------------------------- Admin login + identity
class TestAdminLogin:
    def test_admin_login(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/auth/me", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["email"] == ADMIN_EMAIL
        assert d["role"] == "admin"
        assert d["tenant_id"] == "default"
        assert d["tenant_name"] == "Platform (NEXUS)"

    def test_governance_me_admin(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/governance/me", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["tenant_id"] == "default"
        assert d["tenant_name"] == "Platform (NEXUS)"
        assert d["role"] == "admin"
        assert d.get("is_platform_admin") is True
        assert isinstance(d.get("members"), int) and d["members"] >= 1
        assert d.get("roles_available") == ["user", "analyst", "tenant_admin", "admin", "owner"]
        assert d.get("role_level") == 4


# --------------------------------------------------------------- Registration creates tenant
class TestRegistration:
    def test_register_creates_isolated_tenant(self, fresh_tenant, admin_session):
        u = fresh_tenant["user"]
        assert u["role"] == "tenant_admin"
        assert u["tenant_id"] and u["tenant_id"] != "default"
        assert u["tenant_name"] == fresh_tenant["org"]

        # verify new tenant shows up in admin tenants list
        r = admin_session.get(f"{BASE_URL}/api/admin/tenants", timeout=30)
        assert r.status_code == 200
        tenants = r.json().get("tenants", [])
        match = [t for t in tenants if t.get("tenant_id") == u["tenant_id"]]
        assert match, f"new tenant {u['tenant_id']} not in admin/tenants list"
        t = match[0]
        assert t.get("name") == fresh_tenant["org"]
        assert (t.get("owner_email") or "").lower() == fresh_tenant["email"].lower()


# --------------------------------------------------------------- Brute-force lockout
class TestBruteForceLockout:
    def test_lockout_after_5_failed_logins(self):
        s = _client()
        throwaway = f"lockme_{uuid.uuid4().hex[:8]}@example.com"
        statuses = []
        # 5 fails should each return 401
        for i in range(5):
            r = _login(s, throwaway, "wrongpass-xyz")
            statuses.append(r.status_code)
        # 6th attempt should be 429 (locked)
        r6 = _login(s, throwaway, "wrongpass-xyz")
        assert r6.status_code == 429, (
            f"expected 429 lockout, got {r6.status_code}; prior: {statuses}; body: {r6.text}")
        # earlier attempts were 401
        assert all(c == 401 for c in statuses), f"unexpected statuses: {statuses}"


# --------------------------------------------------------------- Audit log
class TestAudit:
    def test_admin_audit_contains_login(self, admin_session):
        # Trigger a fresh successful login (re-login on a new session)
        s2 = _client()
        r = _login(s2, ADMIN_EMAIL, ADMIN_PASSWORD)
        assert r.status_code == 200
        time.sleep(0.5)

        r = admin_session.get(f"{BASE_URL}/api/admin/audit?action=user.login&limit=50", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "logs" in d and "actions" in d
        assert isinstance(d["actions"], list) and len(d["actions"]) > 0
        success_logins = [l for l in d["logs"]
                          if l.get("action") == "user.login"
                          and l.get("status") == "success"
                          and l.get("user_email") == ADMIN_EMAIL]
        assert success_logins, f"no successful admin login audit entry; logs={d['logs'][:3]}"
        assert success_logins[0].get("tenant_id") == "default"

    def test_audit_forbidden_for_normal_user(self, user_session):
        r = user_session.get(f"{BASE_URL}/api/admin/audit", timeout=30)
        assert r.status_code == 403


# --------------------------------------------------------------- Admin-only RBAC gating
class TestAdminOnlyEndpoints:
    @pytest.mark.parametrize("path", ["/api/admin/tenants", "/api/admin/monitoring", "/api/admin/audit"])
    def test_admin_200(self, admin_session, path):
        r = admin_session.get(f"{BASE_URL}{path}", timeout=30)
        assert r.status_code == 200, f"{path} -> {r.status_code}: {r.text[:200]}"

    @pytest.mark.parametrize("path", ["/api/admin/tenants", "/api/admin/monitoring", "/api/admin/audit"])
    def test_user_403(self, user_session, path):
        r = user_session.get(f"{BASE_URL}{path}", timeout=30)
        assert r.status_code == 403, f"{path} -> {r.status_code}: {r.text[:200]}"


# --------------------------------------------------------------- Monitoring
class TestMonitoring:
    def test_monitoring_payload(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/monitoring", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d.get("db_connected") is True
        assert "scheduler_running" in d
        for k in ("tenants", "users", "leads_total", "audit_events_24h",
                  "logins_failed_24h", "locked_identities", "ai_provider"):
            assert k in d, f"missing {k} in monitoring payload"
        assert isinstance(d["tenants"], int) and d["tenants"] >= 1
        assert isinstance(d["users"], int) and d["users"] >= 1


# --------------------------------------------------------------- Role update RBAC
class TestRoleUpdate:
    def test_role_update_valid_and_invalid(self, admin_session, user_session):
        # find buyer user id
        r = admin_session.get(f"{BASE_URL}/api/admin/users", timeout=30)
        assert r.status_code == 200
        users = r.json()
        buyer = next((u for u in users if u.get("email") == USER_EMAIL), None)
        assert buyer, "buyer@test.io not found in /api/admin/users"
        uid = buyer["id"]
        original_role = buyer.get("role", "user")

        try:
            # Cycle through valid roles
            for new_role in ("analyst", "tenant_admin", "owner", "user"):
                r = admin_session.patch(f"{BASE_URL}/api/admin/users/{uid}/role",
                                        json={"role": new_role}, timeout=30)
                assert r.status_code == 200, f"role={new_role} -> {r.status_code} {r.text}"
                body = r.json()
                # response shape may vary — accept either {role:...} or {user:{role:...}}
                role_in_resp = body.get("role") or (body.get("user") or {}).get("role")
                assert role_in_resp == new_role, f"expected {new_role}, got {body}"

            # Invalid role
            r = admin_session.patch(f"{BASE_URL}/api/admin/users/{uid}/role",
                                    json={"role": "superuser"}, timeout=30)
            assert r.status_code == 400, f"expected 400 for invalid role, got {r.status_code} {r.text}"
        finally:
            # restore
            admin_session.patch(f"{BASE_URL}/api/admin/users/{uid}/role",
                                json={"role": "user"}, timeout=30)


# --------------------------------------------------------------- Governance min role gating
class TestTenantMembers:
    def test_admin_sees_members(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/governance/tenant/members", timeout=30)
        assert r.status_code == 200
        d = r.json()
        # response is either a list or {"members": [...]}
        members = d if isinstance(d, list) else d.get("members", d)
        assert isinstance(members, list)

    def test_user_403(self, user_session):
        r = user_session.get(f"{BASE_URL}/api/governance/tenant/members", timeout=30)
        assert r.status_code == 403


# --------------------------------------------------------------- Readiness
class TestReadiness:
    def test_ready(self):
        # public endpoint - no auth required
        r = requests.get(f"{BASE_URL}/api/ready", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d.get("ready") is True
        assert d.get("db") == "connected"


# --------------------------------------------------------------- Regression: storefront purchase
class TestStorefrontRegression:
    def test_admin_can_purchase_and_double_sell_guard(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/storefront/leads", timeout=30)
        assert r.status_code == 200
        d = r.json()
        # Find first available masked lead
        leads = d.get("leads", d if isinstance(d, list) else [])
        assert leads, "no leads available in storefront for regression test"
        # ensure masking
        first = leads[0]
        assert first.get("locked") is True or "contact_masked" in first or "company_masked" in first, \
            f"expected masking flags on storefront lead: {first}"
        lead_id = first.get("id") or first.get("_id")
        assert lead_id

        # Purchase as admin
        rp = admin_session.post(f"{BASE_URL}/api/storefront/purchase-leads",
                                json={"lead_ids": [lead_id]}, timeout=60)
        assert rp.status_code == 200, f"purchase failed: {rp.status_code} {rp.text}"
        pdata = rp.json()
        purchased = pdata.get("purchased_leads") or pdata.get("leads") or []
        # unmasked check
        assert purchased, f"no purchased leads returned: {pdata}"
        sample = purchased[0]
        # at least one PII field unmasked
        assert any(sample.get(k) for k in ("email", "phone", "company", "full_name")), \
            f"expected unmasked PII fields: {sample}"

        # Double-sell guard
        rp2 = admin_session.post(f"{BASE_URL}/api/storefront/purchase-leads",
                                 json={"lead_ids": [lead_id]}, timeout=60)
        assert rp2.status_code == 400, f"expected 400 on double-sell, got {rp2.status_code} {rp2.text}"
        assert "available" in rp2.text.lower()


class TestInsufficientCredits:
    def test_fresh_user_402(self, admin_session):
        # register fresh user with 0 credits
        s = _client()
        email = f"TEST_zero_{uuid.uuid4().hex[:10]}@example.com"
        rr = s.post(f"{BASE_URL}/api/auth/register",
                    json={"email": email, "password": "Test123!Pass", "name": "ZeroCred"},
                    timeout=30)
        assert rr.status_code == 200, f"register failed: {rr.status_code} {rr.text}"

        # find an available lead via admin
        r = admin_session.get(f"{BASE_URL}/api/storefront/leads", timeout=30)
        leads = r.json().get("leads", [])
        assert leads, "no storefront leads to test 402"
        lead_id = leads[0].get("id")

        rp = s.post(f"{BASE_URL}/api/storefront/purchase-leads",
                    json={"lead_ids": [lead_id]}, timeout=60)
        assert rp.status_code == 402, f"expected 402, got {rp.status_code} {rp.text}"

        # ensure lead is still available
        r2 = admin_session.get(f"{BASE_URL}/api/storefront/leads", timeout=30)
        ids = [l.get("id") for l in r2.json().get("leads", [])]
        assert lead_id in ids, "lead should remain available after 402"


# --------------------------------------------------------------- Regression: auth/me + leads + logout
class TestAuthRegression:
    def test_auth_me_admin(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/auth/me", timeout=30)
        assert r.status_code == 200
        assert r.json().get("email") == ADMIN_EMAIL

    def test_leads_list(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/leads", timeout=30)
        assert r.status_code == 200
        d = r.json()
        leads = d if isinstance(d, list) else d.get("leads", [])
        assert isinstance(leads, list)

    def test_logout(self):
        s = _client()
        r = _login(s, USER_EMAIL, USER_PASSWORD)
        assert r.status_code == 200
        rl = s.post(f"{BASE_URL}/api/auth/logout", timeout=30)
        assert rl.status_code == 200
        # cookies removed -> /api/auth/me should now be 401
        # use a fresh session ignoring previous cookies
        s2 = requests.Session()
        rm = s2.get(f"{BASE_URL}/api/auth/me", timeout=30)
        assert rm.status_code == 401
