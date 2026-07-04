from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse


STATIC_DIR = Path(__file__).resolve().parent / "static"
LEAD_CONTROL_CENTER_PATH = STATIC_DIR / "lead-control-center.html"

app = FastAPI(title="NEXUS B2B Lead Generation API", version="0.1.0")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/lead-control-center", response_class=HTMLResponse)
def lead_control_center() -> HTMLResponse:
    """
    Serves the Lead Control Center HTML dashboard.
    Make sure lead-control-center.html is placed in app/static/.
    """
    if not LEAD_CONTROL_CENTER_PATH.exists():
        return HTMLResponse(
            "<h2>Lead Control Center file not found.</h2>"
            "<p>Place lead-control-center.html inside app/static/.</p>",
            status_code=404,
        )

    return HTMLResponse(LEAD_CONTROL_CENTER_PATH.read_text(encoding="utf-8"))


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
