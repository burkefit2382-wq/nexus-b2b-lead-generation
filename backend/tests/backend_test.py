"""NEXUS backend e2e tests (pytest)."""
import os
import time
import uuid
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://cloud-saas-hub.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

ADMIN_EMAIL = "admin@nexus.io"
ADMIN_PASS = "nexus123"


# ---------------- fixtures ----------------
@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=20)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="session")
def user_account():
    """Fresh non-admin user."""
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    pw = "Passw0rd!"
    s = requests.Session()
    r = s.post(f"{API}/auth/register", json={"email": email, "password": pw, "name": "Tester"}, timeout=20)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["role"] == "user"
    return {"session": s, "email": email, "password": pw, "id": body["id"]}


# ---------------- health ----------------
def test_health():
    r = requests.get(f"{API}/health", timeout=10)
    assert r.status_code == 200
    assert r.json().get("status") == "online"


# ---------------- auth ----------------
def test_admin_login_and_me(admin_session):
    r = admin_session.get(f"{API}/auth/me", timeout=10)
    assert r.status_code == 200
    me = r.json()
    assert me["email"] == ADMIN_EMAIL
    assert me["role"] == "admin"


def test_register_user_returns_cookies(user_account):
    s = user_account["session"]
    # cookie should be set
    assert any(c.name == "access_token" for c in s.cookies)
    r = s.get(f"{API}/auth/me", timeout=10)
    assert r.status_code == 200
    assert r.json()["email"] == user_account["email"]


def test_login_invalid_password():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrongpass"}, timeout=10)
    assert r.status_code == 401


# ---------------- RBAC ----------------
def test_admin_list_users_works_for_admin(admin_session):
    r = admin_session.get(f"{API}/admin/users", timeout=10)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_admin_list_users_forbidden_for_user(user_account):
    r = user_account["session"].get(f"{API}/admin/users", timeout=10)
    assert r.status_code == 403


def test_admin_role_update(admin_session, user_account):
    uid = user_account["id"]
    r = admin_session.patch(f"{API}/admin/users/{uid}/role", json={"role": "admin"}, timeout=10)
    assert r.status_code == 200
    assert r.json()["role"] == "admin"
    # revert
    admin_session.patch(f"{API}/admin/users/{uid}/role", json={"role": "user"}, timeout=10)


# ---------------- API keys ----------------
def test_api_key_lifecycle(admin_session):
    r = admin_session.post(f"{API}/keys", json={"name": "TEST_key"}, timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    raw = body["api_key"]
    kid = body["id"]
    assert raw.startswith("nxs_")
    assert body["prefix"].startswith("nxs_")

    # list
    lst = admin_session.get(f"{API}/keys", timeout=10)
    assert lst.status_code == 200
    assert any(k["id"] == kid for k in lst.json())

    # Use X-API-Key on a fresh session (no cookies)
    bare = requests.Session()
    r2 = bare.get(f"{API}/auth/me", headers={"X-API-Key": raw}, timeout=10)
    assert r2.status_code == 200
    assert r2.json()["email"] == ADMIN_EMAIL

    # revoke
    d = admin_session.delete(f"{API}/keys/{kid}", timeout=10)
    assert d.status_code == 200

    # revoked key should now fail
    r3 = requests.get(f"{API}/auth/me", headers={"X-API-Key": raw}, timeout=10)
    assert r3.status_code == 401


# ---------------- leads ----------------
def test_leads_list_has_seed(admin_session):
    r = admin_session.get(f"{API}/leads", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 4
    assert isinstance(data["leads"], list)


def test_leads_stats(admin_session):
    r = admin_session.get(f"{API}/leads/stats", timeout=10)
    assert r.status_code == 200
    s = r.json()
    for key in ("total", "hot_leads", "sold", "total_revenue"):
        assert key in s


def test_leads_filter_and_search(admin_session):
    r = admin_session.get(f"{API}/leads", params={"category": "cleaning"}, timeout=10)
    assert r.status_code == 200
    assert all(l["category"] == "cleaning" for l in r.json()["leads"])

    r2 = admin_session.get(f"{API}/leads", params={"search": "Marcus"}, timeout=10)
    assert r2.status_code == 200
    assert any("Marcus" in (l.get("full_name") or "") for l in r2.json()["leads"])


def test_lead_create_sell_delete(admin_session):
    payload = {"category": "cleaning", "full_name": "TEST_User", "email": "t@t.io",
               "phone": "+1 555 555 5555", "city": "Austin", "state": "TX",
               "source_site": "Test", "source_url": "https://t.io", "raw_text": "test"}
    r = admin_session.post(f"{API}/leads", json=payload, timeout=10)
    assert r.status_code == 200
    lead = r.json()
    lid = lead["id"]
    assert lead["full_name"] == "TEST_User"

    # sell
    s = admin_session.patch(f"{API}/leads/{lid}/sell", params={"price": 199.0}, timeout=10)
    assert s.status_code == 200

    # verify via list - find it
    listing = admin_session.get(f"{API}/leads", params={"search": "TEST_User"}, timeout=10).json()
    matched = [l for l in listing["leads"] if l["id"] == lid]
    assert matched and matched[0]["is_sold"] is True
    assert matched[0]["sold_price"] == 199.0

    # delete
    d = admin_session.delete(f"{API}/leads/{lid}", timeout=10)
    assert d.status_code == 200


# ---------------- OSINT ----------------
def test_osint_dns(admin_session):
    r = admin_session.post(f"{API}/osint/dns", json={"target": "google.com"}, timeout=20)
    assert r.status_code == 200
    body = r.json()
    assert body["tool"] == "dns"
    # at least one record type should resolve
    recs = body.get("records") or {}
    assert any(len(recs.get(k, [])) > 0 for k in ("A", "MX", "NS", "TXT"))


def test_osint_ip(admin_session):
    r = admin_session.post(f"{API}/osint/ip", json={"target": "8.8.8.8"}, timeout=20)
    assert r.status_code == 200
    assert r.json()["tool"] == "ip_lookup"


def test_osint_phone(admin_session):
    r = admin_session.post(f"{API}/osint/phone", json={"target": "+14085551234"}, timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body["tool"] == "phone"
    assert "valid" in body


def test_osint_reports_list(admin_session):
    r = admin_session.get(f"{API}/osint/reports", timeout=10)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1


# ---------------- AI (graceful degradation) ----------------
def test_ai_chat_graceful(admin_session):
    r = admin_session.post(f"{API}/enrichment/chat", json={"message": "hi"}, timeout=30)
    assert r.status_code == 200  # must not crash
    body = r.json()
    # either content or graceful error
    assert "response" in body or "error" in body


def test_ai_enrich_graceful(admin_session):
    # create a raw lead then enrich
    payload = {"category": "cleaning", "full_name": "TEST_Enrich", "raw_text": "needs cleaning soon"}
    lid = admin_session.post(f"{API}/leads", json=payload, timeout=10).json()["id"]
    r = admin_session.post(f"{API}/enrichment/enrich", json={"lead_id": lid}, timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert "error" in body or "summary" in body
    admin_session.delete(f"{API}/leads/{lid}", timeout=10)


# ---------------- logout ----------------
def test_logout_clears_cookie():
    s = requests.Session()
    s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=10)
    r = s.post(f"{API}/auth/logout", timeout=10)
    assert r.status_code == 200
    me = s.get(f"{API}/auth/me", timeout=10)
    assert me.status_code == 401


# ---------------- 24/7 Scraper Engine ----------------
def test_scraper_status_shape(admin_session):
    r = admin_session.get(f"{API}/scraper/status", timeout=10)
    assert r.status_code == 200
    s = r.json()
    for k in ("scheduler_running", "interval_min", "min_score", "found",
              "qualified", "cycles", "total_scraped_leads"):
        assert k in s, f"missing {k} in {s}"
    assert s["scheduler_running"] is True


def test_scraper_config_get_and_admin_put(admin_session):
    r = admin_session.get(f"{API}/scraper/config", timeout=10)
    assert r.status_code == 200
    cfg = r.json()
    assert "sources" in cfg and isinstance(cfg["sources"], list)
    providers = {s.get("provider") for s in cfg["sources"]}
    assert {"hackernews", "github", "reddit"}.issubset(providers)

    # admin PUT
    new_cfg = {
        "enabled": True,
        "interval_min": 30,
        "min_score": 55.0,
        "use_ai": True,
        "ai_model": "deepseek",
        "sources": cfg["sources"],
    }
    p = admin_session.put(f"{API}/scraper/config", json=new_cfg, timeout=10)
    assert p.status_code == 200, p.text
    assert p.json().get("updated") is True


def test_scraper_config_put_forbidden_for_user(user_account):
    payload = {"enabled": True, "interval_min": 30, "min_score": 55.0,
               "use_ai": True, "ai_model": "deepseek", "sources": []}
    r = user_account["session"].put(f"{API}/scraper/config", json=payload, timeout=10)
    assert r.status_code == 403


def test_scraper_trigger_increments_cycles_and_feed(admin_session):
    before = admin_session.get(f"{API}/scraper/status", timeout=10).json()
    t = admin_session.post(f"{API}/scraper/trigger", timeout=10)
    assert t.status_code == 200
    assert t.json().get("triggered") is True

    # wait up to ~40s for cycle to complete
    cycles_after = before["cycles"]
    for _ in range(20):
        time.sleep(2)
        st = admin_session.get(f"{API}/scraper/status", timeout=10).json()
        if st["cycles"] > before["cycles"] and st["status"] == "idle":
            cycles_after = st["cycles"]
            break
    assert cycles_after > before["cycles"], f"cycle did not complete; status={st}"
    # found should be >=0 (HN/GitHub may be rate-limited but call must succeed)
    assert st["found"] >= before["found"]

    # feed
    f = admin_session.get(f"{API}/scraper/feed", timeout=10)
    assert f.status_code == 200
    feed = f.json()
    assert isinstance(feed, list)
    # All scraped leads must have scraped=true and source_site matching domain
    for l in feed:
        assert l.get("scraped") is True
        site = (l.get("source_site") or "").lower()
        url = (l.get("source_url") or "").lower()
        # source_site should NOT be hardcoded to Reddit unless url is reddit
        if "reddit" not in url and site == "reddit":
            pytest.fail(f"source_site=Reddit but url is {url}")
        if "news.ycombinator" in url:
            assert "hacker news" in site
        if "github.com" in url:
            assert site == "github"


# ---------------- AI model selection ----------------
def test_ai_model_status_lists_both(admin_session):
    r = admin_session.get(f"{API}/enrichment/model-status", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert "models" in body
    assert "deepseek" in body["models"]
    assert "qwen" in body["models"]
    assert body["models"]["deepseek"]
    assert body["models"]["qwen"]


@pytest.mark.parametrize("model", ["deepseek", "qwen"])
def test_ai_chat_both_models_graceful(admin_session, model):
    r = admin_session.post(f"{API}/enrichment/chat",
                           json={"message": "hi", "model": model}, timeout=30)
    assert r.status_code == 200, r.text  # NEVER 500
    body = r.json()
    assert "response" in body or "error" in body
