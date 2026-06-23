from fastapi import FastAPI

app = FastAPI(title="NEXUS B2B Lead Generation API", version="0.1.0")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/leads/mock")
def get_mock_leads(limit: int = 5) -> dict[str, list[dict[str, str]]]:
    safe_limit = max(1, min(limit, 50))
    leads = [
        {
            "name": f"Lead {index}",
            "company": f"Company {index}",
            "email": f"lead{index}@example.com",
        }
        for index in range(1, safe_limit + 1)
    ]
    return {"leads": leads}
