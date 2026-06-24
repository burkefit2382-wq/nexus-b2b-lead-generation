import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_search_leads_post():
    response = client.post(
        "/api/leads/search",
        json={"company_name": "Acme Corp", "limit": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["leads"]) == 5
    assert data["query"] == "Acme Corp"
    lead = data["leads"][0]
    assert lead["company"] == "Acme Corp"
    assert "@acmecorp.com" in lead["email"]
    assert lead["score"] >= 40


def test_search_leads_get():
    response = client.get("/api/leads/search?company_name=TestCo&limit=3")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["query"] == "TestCo"


def test_search_leads_with_filters():
    response = client.post(
        "/api/leads/search",
        json={
            "company_name": "TechFirm",
            "industry": "SaaS",
            "location": "New York",
            "limit": 2,
        },
    )
    assert response.status_code == 200
    data = response.json()
    for lead in data["leads"]:
        assert lead["industry"] == "SaaS"
        assert lead["location"] == "New York"


def test_search_leads_deterministic():
    r1 = client.post("/api/leads/search", json={"company_name": "Stable Inc", "limit": 3})
    r2 = client.post("/api/leads/search", json={"company_name": "Stable Inc", "limit": 3})
    assert r1.json()["leads"] == r2.json()["leads"]
