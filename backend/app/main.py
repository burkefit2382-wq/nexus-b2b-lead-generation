import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse


STATIC_DIR = Path(__file__).resolve().parent / "static"
LEAD_CONTROL_CENTER_PATH = STATIC_DIR / "lead-control-center.html"
APP_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("NEXUS_DATA_DIR", APP_ROOT / "data"))
SCRAPER_DIR = DATA_DIR / "scrapers"
SCRAPER_SUMMARY_PATH = SCRAPER_DIR / "latest_summary.json"
SCRAPER_STATE_PATH = SCRAPER_DIR / "worker_state.json"
SCRAPER_JSONL_PATH = SCRAPER_DIR / "tampa_bay_real_estate_leads.jsonl"

app = FastAPI(title="NEXUS B2B Lead Generation API", version="0.1.0")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health")
def api_health() -> dict[str, Any]:
    return {
        "ok": True,
        "status": "healthy",
        "service": "nexus-b2b-lead-generation-api",
        "healthz": "/healthz",
        "checkedAt": utc_now(),
    }


@app.get("/api/scraper-queue")
def scraper_queue() -> dict[str, Any]:
    summary = load_json(SCRAPER_SUMMARY_PATH)
    errors = summary.get("errors", []) if isinstance(summary.get("errors"), list) else []
    return {
        "ok": True,
        "status": "Queue Idle",
        "queued": 0,
        "running": 0,
        "failedLast24h": len(errors),
        "lastRunAt": summary.get("last_run_at"),
        "source": summary.get("source", "No scraper summary available"),
    }


@app.get("/api/lead-stats")
def lead_stats() -> dict[str, Any]:
    summary = load_json(SCRAPER_SUMMARY_PATH)
    total = int(summary.get("total_records") or count_lines(SCRAPER_JSONL_PATH) or 0)
    last_run_at = str(summary.get("last_run_at") or "")
    new_records = int(summary.get("new_records") or 0)
    today = new_records if is_today(last_run_at) else 0
    week = total if is_within_days(last_run_at, 7) else 0
    return {
        "ok": True,
        "today": today,
        "week": week,
        "total": total,
        "lastRunAt": last_run_at or None,
        "source": "scraper summary" if summary else "default",
        "quality": summary.get("quality") or {},
    }


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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return 0


def parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def is_today(value: str) -> bool:
    parsed = parse_datetime(value)
    if parsed is None:
        return False
    return parsed.astimezone(timezone.utc).date() == datetime.now(timezone.utc).date()


def is_within_days(value: str, days: int) -> bool:
    parsed = parse_datetime(value)
    if parsed is None:
        return False
    age = datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)
    return 0 <= age.total_seconds() <= days * 24 * 60 * 60
