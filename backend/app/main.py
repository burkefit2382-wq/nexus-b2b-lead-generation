import json
import logging
import os
import socket
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from .api.leads import router as leads_router
from .api.membership import router as membership_router
from .services import config
from .services import hubspot as hubspot_service
from .services.database import run_migrations


STATIC_DIR = Path(__file__).resolve().parent / "static"
LEAD_CONTROL_CENTER_PATH = STATIC_DIR / "lead-control-center.html"
APP_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = config.NEXUS_DATA_DIR
SCRAPER_DIR = DATA_DIR / "scrapers"
SCRAPER_SUMMARY_PATH = SCRAPER_DIR / "latest_summary.json"
SCRAPER_STATE_PATH = SCRAPER_DIR / "worker_state.json"
SCRAPER_JSONL_PATH = SCRAPER_DIR / "tampa_bay_real_estate_leads.jsonl"
ALLOWED_EVENT_NAMES = {
    "page_view",
    "form_start",
    "generate_lead",
    "phone_click",
    "email_click",
    "quote_request",
    "qualified_lead",
    "closed_deal",
    "bad_lead",
}
EXTERNAL_DEPENDENCY_TIMEOUT_SECONDS = 1.5
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 120
_rate_limit_buckets: dict[tuple[str, str], list[float]] = {}
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations(config.database_url())
    yield


app = FastAPI(title="NEXUS B2B Lead Generation API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.tracking_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.include_router(leads_router, prefix="/leads", tags=["Leads"])
app.include_router(membership_router, prefix="/api/membership", tags=["Membership"])


@app.middleware("http")
async def rate_limit_public_requests(request: Request, call_next):
    request_id = request.headers.get("x-request-id", "").strip() or str(uuid.uuid4())
    request.state.request_id = request_id
    limit = rate_limit_max_requests()
    window = rate_limit_window_seconds()
    remaining = limit
    reset_seconds = window

    if is_rate_limited_endpoint(request):
        allowed, remaining, reset_seconds = allow_request(request, limit, window)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "ok": False,
                    "error": "Rate limit exceeded. Retry after the current window resets.",
                    "requestId": request_id,
                },
                headers=rate_limit_headers(limit, remaining, reset_seconds, request_id),
            )

    response = await call_next(request)
    for header, value in rate_limit_headers(limit, remaining, reset_seconds, request_id).items():
        response.headers.setdefault(header, value)
    return response


@app.get("/health")
def healthcheck(response: Response) -> dict[str, Any]:
    return write_health_response("nexus-b2b-lead-generation-api", response)


@app.get("/healthz")
def healthz(response: Response) -> dict[str, Any]:
    return write_health_response("nexus-b2b-lead-generation-api", response)


@app.get("/api/health")
def api_health(response: Response) -> dict[str, Any]:
    payload = write_health_response("nexus-b2b-lead-generation-api", response)
    payload["healthz"] = "/healthz"
    return payload


@app.get("/api/config-status")
def config_status() -> dict[str, bool | str]:
    status = hubspot_service.hubspot_status()
    return {
        "ok": True,
        "databaseUrlConfigured": bool(config.database_url()),
        "r2Configured": config.r2_configured(),
        "resendConfigured": config.resend_configured(),
        "jwtConfigured": config.jwt_configured(),
        "hubspotConfigured": bool(status["configured"]),
        "stripeConfigured": config.stripe_configured(),
        "checkedAt": utc_now(),
    }


@app.get("/api/hubspot-status")
@app.get("/api/crm-status")
def api_hubspot_status() -> dict[str, Any]:
    return {"ok": True, "hubspot": hubspot_service.hubspot_status()}


@app.post("/api/hubspot-export")
@app.post("/api/crm-export")
def api_hubspot_export(payload: dict[str, Any], response: Response) -> dict[str, Any]:
    token = hubspot_service.hubspot_access_token()
    if not token:
        response.status_code = 503
        return {"ok": False, "error": "HubSpot is not configured.", "missing": hubspot_service.hubspot_missing_token_names()}

    lead = payload.get("lead")
    if not isinstance(lead, dict):
        response.status_code = 400
        return {"ok": False, "error": "Request requires a lead object."}

    try:
        properties = hubspot_service.hubspot_contact_properties(lead)
    except ValueError as exc:
        response.status_code = 400
        return {"ok": False, "error": str(exc)}

    try:
        result = hubspot_service.upsert_hubspot_contact(token, properties)
    except hubspot_service.HubSpotExportError as exc:
        response.status_code = 502
        return {
            "ok": False,
            "error": str(exc),
            "status": exc.status,
            "detail": exc.detail,
        }

    return {
        "ok": True,
        "message": f"HubSpot contact {result['action']}.",
        "hubspot": {"id": result["id"], "action": result["action"]},
        "properties": {key: value for key, value in properties.items() if key != "email"},
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


@app.post("/api/event", status_code=201)
def create_event(payload: dict[str, Any], response: Response) -> dict[str, str | bool]:
    try:
        event = normalize_event_payload(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    database_url = config.database_url()
    if not database_url:
        response.status_code = 503
        return {"ok": False, "error": "DATABASE_URL is not configured for event tracking."}

    try:
        saved = save_event(database_url, event)
    except Exception as exc:  # noqa: BLE001 - tracking clients should receive JSON failures.
        raise HTTPException(status_code=500, detail=f"Event save failed: {exc}") from exc

    return {"ok": True, **saved}


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


def write_health_response(service_name: str, response: Response) -> dict[str, Any]:
    dependencies = collect_dependency_health()
    required_failures = [name for name, status in dependencies.items() if status["required"] and not status["healthy"]]
    optional_failures = [name for name, status in dependencies.items() if not status["required"] and not status["healthy"]]
    status = "healthy"
    if required_failures:
        status = "unhealthy"
        response.status_code = 503
    elif optional_failures:
        status = "degraded"

    return {
        "ok": not required_failures,
        "status": status,
        "service": service_name,
        "checkedAt": utc_now(),
        "dependencies": dependencies,
    }


def collect_dependency_health() -> dict[str, dict[str, Any]]:
    database_url = config.database_url()
    return {
        "database": database_dependency_status(database_url),
        "resend": external_dependency_status(
            configured=config.resend_configured(),
            host="api.resend.com",
            label="Resend",
            required=False,
        ),
        "stripe": external_dependency_status(
            configured=config.stripe_configured(),
            host="api.stripe.com",
            label="Stripe",
            required=False,
        ),
        "hubspot": external_dependency_status(
            configured=bool(hubspot_service.hubspot_access_token()),
            host="api.hubapi.com",
            label="HubSpot",
            required=False,
        ),
    }


def database_dependency_status(database_url: str) -> dict[str, Any]:
    if not database_url:
        return dependency_status(
            label="Postgres",
            configured=False,
            healthy=False,
            required=True,
            detail="DATABASE_URL is not configured.",
        )

    parsed = urlparse(database_url)
    host = parsed.hostname
    port = parsed.port or 5432
    if not host:
        return dependency_status(
            label="Postgres",
            configured=True,
            healthy=False,
            required=True,
            detail="DATABASE_URL is missing a hostname.",
        )

    healthy, detail = probe_tcp_endpoint(host, port)
    return dependency_status("Postgres", True, healthy, True, detail)


def external_dependency_status(*, configured: bool, host: str, label: str, required: bool) -> dict[str, Any]:
    if not configured:
        return dependency_status(label, False, False, required, f"{label} is not configured.")
    healthy, detail = probe_tcp_endpoint(host, 443)
    return dependency_status(label, True, healthy, required, detail)


def dependency_status(label: str, configured: bool, healthy: bool, required: bool, detail: str) -> dict[str, Any]:
    return {
        "name": label,
        "configured": configured,
        "healthy": healthy,
        "required": required,
        "detail": detail,
    }


def probe_tcp_endpoint(host: str, port: int) -> tuple[bool, str]:
    timeout = dependency_timeout_seconds()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, f"Connected to {host}:{port}."
    except OSError as exc:
        return False, f"Connection failed to {host}:{port}: {exc}"


def dependency_timeout_seconds() -> float:
    raw_value = os.environ.get("HEALTHCHECK_TIMEOUT_SECONDS", str(EXTERNAL_DEPENDENCY_TIMEOUT_SECONDS)).strip()
    try:
        return max(0.1, min(float(raw_value), 10.0))
    except ValueError:
        return EXTERNAL_DEPENDENCY_TIMEOUT_SECONDS


def is_rate_limited_endpoint(request: Request) -> bool:
    return request.method == "POST" and (request.url.path.startswith("/api/") or request.url.path.startswith("/leads"))


def allow_request(request: Request, limit: int, window: int) -> tuple[bool, int, int]:
    client_host = client_ip(request)
    bucket_key = (client_host, request.url.path)
    now = datetime.now(timezone.utc).timestamp()
    cutoff = now - window
    bucket = [stamp for stamp in _rate_limit_buckets.get(bucket_key, []) if stamp >= cutoff]
    allowed = len(bucket) < limit
    if allowed:
        bucket.append(now)
    _rate_limit_buckets[bucket_key] = bucket
    remaining = max(0, limit - len(bucket))
    reset_seconds = max(0, int(window - (now - bucket[0]))) if bucket else window
    return allowed, remaining, reset_seconds


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded:
        return forwarded
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def rate_limit_headers(limit: int, remaining: int, reset_seconds: int, request_id: str) -> dict[str, str]:
    return {
        "X-Request-Id": request_id,
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(max(0, remaining)),
        "X-RateLimit-Reset": str(max(0, reset_seconds)),
    }


def rate_limit_max_requests() -> int:
    raw_value = os.environ.get("PUBLIC_RATE_LIMIT_MAX_REQUESTS", str(RATE_LIMIT_MAX_REQUESTS)).strip()
    try:
        return max(1, min(int(raw_value), 10000))
    except ValueError:
        return RATE_LIMIT_MAX_REQUESTS


def rate_limit_window_seconds() -> int:
    raw_value = os.environ.get("PUBLIC_RATE_LIMIT_WINDOW_SECONDS", str(RATE_LIMIT_WINDOW_SECONDS)).strip()
    try:
        return max(1, min(int(raw_value), 3600))
    except ValueError:
        return RATE_LIMIT_WINDOW_SECONDS


def normalize_event_payload(payload: dict[str, Any]) -> dict[str, Any]:
    event_name = str(payload.get("event_name") or "").strip()
    if event_name not in ALLOWED_EVENT_NAMES:
        allowed = ", ".join(sorted(ALLOWED_EVENT_NAMES))
        raise ValueError(f"event_name must be one of: {allowed}.")

    event_data = payload.get("event_data") or {}
    if not isinstance(event_data, dict):
        raise ValueError("event_data must be a JSON object when provided.")
    event_data = dict(event_data)

    visitor_id, external_visitor_id = uuid_or_external(payload.get("visitor_id"))
    lead_id, external_lead_id = uuid_or_external(payload.get("lead_id"))
    if external_visitor_id:
        event_data["external_visitor_id"] = external_visitor_id
    if external_lead_id:
        event_data["external_lead_id"] = external_lead_id

    return {
        "event_name": event_name,
        "client_id": clean_text(payload.get("client_id"), 256),
        "visitor_id": visitor_id,
        "lead_id": lead_id,
        "page_url": clean_text(payload.get("page_url"), 2048),
        "referrer": clean_text(payload.get("referrer"), 2048),
        "utm_source": clean_text(payload.get("utm_source"), 256),
        "utm_medium": clean_text(payload.get("utm_medium"), 256),
        "utm_campaign": clean_text(payload.get("utm_campaign"), 256),
        "utm_content": clean_text(payload.get("utm_content"), 256),
        "utm_term": clean_text(payload.get("utm_term"), 256),
        "gclid": clean_text(payload.get("gclid"), 512),
        "msclkid": clean_text(payload.get("msclkid"), 512),
        "fbclid": clean_text(payload.get("fbclid"), 512),
        "event_data": event_data,
    }


def save_event(database_url: str, event: dict[str, Any]) -> dict[str, str]:
    import psycopg

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cursor:
            visitor_id = resolve_visitor_id(cursor, event)
            cursor.execute(
                """
                INSERT INTO events (visitor_id, lead_id, event_name, page_url, event_data)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                RETURNING id
                """,
                (
                    visitor_id,
                    resolve_lead_id(cursor, event),
                    event["event_name"],
                    event["page_url"],
                    json.dumps(event["event_data"], sort_keys=True),
                ),
            )
            event_id = cursor.fetchone()[0]
    return {"event_id": str(event_id), "visitor_id": str(visitor_id)}


def resolve_visitor_id(cursor: Any, event: dict[str, Any]) -> uuid.UUID:
    if event["visitor_id"]:
        cursor.execute(
            """
            INSERT INTO visitors (
              id, client_id, first_page_url, referrer, utm_source, utm_medium,
              utm_campaign, utm_content, utm_term, gclid, msclkid, fbclid
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET last_seen_at = NOW()
            RETURNING id
            """,
            (
                event["visitor_id"],
                event["client_id"],
                event["page_url"],
                event["referrer"],
                event["utm_source"],
                event["utm_medium"],
                event["utm_campaign"],
                event["utm_content"],
                event["utm_term"],
                event["gclid"],
                event["msclkid"],
                event["fbclid"],
            ),
        )
        return cursor.fetchone()[0]

    if event["client_id"]:
        cursor.execute("SELECT id FROM visitors WHERE client_id = %s ORDER BY last_seen_at DESC LIMIT 1", (event["client_id"],))
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE visitors SET last_seen_at = NOW() WHERE id = %s RETURNING id", (row[0],))
            return cursor.fetchone()[0]

    cursor.execute(
        """
        INSERT INTO visitors (
          client_id, first_page_url, referrer, utm_source, utm_medium,
          utm_campaign, utm_content, utm_term, gclid, msclkid, fbclid
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            event["client_id"],
            event["page_url"],
            event["referrer"],
            event["utm_source"],
            event["utm_medium"],
            event["utm_campaign"],
            event["utm_content"],
            event["utm_term"],
            event["gclid"],
            event["msclkid"],
            event["fbclid"],
        ),
    )
    return cursor.fetchone()[0]


def resolve_lead_id(cursor: Any, event: dict[str, Any]) -> uuid.UUID | None:
    if not event["lead_id"]:
        return None
    cursor.execute("SELECT id FROM leads WHERE id = %s LIMIT 1", (event["lead_id"],))
    row = cursor.fetchone()
    if row:
        return row[0]
    event["event_data"]["unmatched_lead_id"] = str(event["lead_id"])
    return None


def clean_text(value: Any, max_length: int) -> str:
    text = "" if value is None else str(value).strip()
    return text[:max_length]


def uuid_or_external(value: Any) -> tuple[uuid.UUID | None, str]:
    text = clean_text(value, 256)
    if not text:
        return None, ""
    try:
        return uuid.UUID(text), ""
    except ValueError:
        return None, text


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
