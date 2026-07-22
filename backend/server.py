"""
Local launch server for LeadGen Virtual Hub.

Serves the static site and exposes POST /api/waitlist. Waitlist submissions are
stored locally in data/waitlist_requests.jsonl. If Resend environment variables
are configured and the resend package is installed, the server also sends an
internal notification email.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT.parent / "data"


def load_local_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_local_env()
WAITLIST_PATH = DATA_DIR / "waitlist_requests.jsonl"
LEAD_PACKAGE_REQUESTS_PATH = DATA_DIR / "lead_package_requests.jsonl"
FULFILLMENT_EVENTS_PATH = DATA_DIR / "fulfillment_events.jsonl"
OSINT_REPORTS_PATH = DATA_DIR / "osint_report_requests.jsonl"
HUBSPOT_EXPORTS_PATH = DATA_DIR / "hubspot_exports.jsonl"
HUBSPOT_DEFAULT_PORTAL_ID = "246668830"
SCRAPER_DIR = DATA_DIR / "scrapers"
SCRAPER_SUMMARY_PATH = SCRAPER_DIR / "latest_summary.json"
SCRAPER_JSONL_PATH = SCRAPER_DIR / "tampa_bay_real_estate_leads.jsonl"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
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
HQ_FLORIDA_LEAD_COUNT = 137
HQ_FLORIDA_PRICING = (
    {"quantity": 10, "price": 350, "priceId": "price_tb_leads_10_350"},
    {"quantity": 25, "price": 700, "priceId": "price_tb_leads_25_700"},
    {"quantity": 50, "price": 1000, "priceId": "price_tb_leads_50_1000"},
)
STRIPE_API_VERSION = os.environ.get("STRIPE_API_VERSION", "2026-06-24.dahlia")
STRIPE_CATALOG = {
    "price_tb_leads_10_350": {
        "name": "Tampa Bay 10-Lead Sprint",
        "price": "$350",
        "mode": "payment",
        "category": "lead_workflow",
        "quantity": 10,
        "region": "Pinellas, Hillsborough, Pasco, Hernando",
    },
    "price_tb_leads_25_700": {
        "name": "Tampa Bay 25-Lead Growth Sprint",
        "price": "$700",
        "mode": "payment",
        "category": "lead_workflow",
        "quantity": 25,
        "region": "Pinellas, Hillsborough, Pasco, Hernando",
    },
    "price_tb_leads_50_1000": {
        "name": "Tampa Bay 50-Lead Domination Sprint",
        "price": "$1,000",
        "mode": "payment",
        "category": "lead_workflow",
        "quantity": 50,
        "region": "Pinellas, Hillsborough, Pasco, Hernando",
    },
    "price_lead_drops_99": {
        "name": "Lead Drops Subscription",
        "price": "$99/mo",
        "mode": "subscription",
        "category": "recurring_revenue",
    },
    "price_territory_exclusive_499": {
        "name": "Territory Exclusivity Subscription",
        "price": "$499/mo",
        "mode": "subscription",
        "category": "recurring_revenue",
    },
    "price_osint_monitoring_49": {
        "name": "OSINT Monitoring Subscription",
        "price": "$49/mo",
        "mode": "subscription",
        "category": "recurring_revenue",
    },
    "price_business_intel_99": {
        "name": "Business Intelligence Subscription",
        "price": "$99/mo",
        "mode": "subscription",
        "category": "recurring_revenue",
    },
    "price_api_license_2000": {
        "name": "Nexus API Access License",
        "price": "$2,000",
        "mode": "payment",
        "category": "api_access",
    },
    "price_api_access_500": {
        "name": "Nexus API Ongoing Access",
        "price": "$500/mo",
        "mode": "subscription",
        "category": "api_access",
    },
    "price_white_label_agency_1000": {
        "name": "White-Label LeadGen Agency Subscription",
        "price": "$1,000/mo",
        "mode": "subscription",
        "category": "agency_whitelabel",
    },
    "price_people_osint_report_25": {
        "name": "Authorized People OSINT Report",
        "price": "$25",
        "mode": "payment",
        "category": "osint_report",
    },
    "price_business_osint_report_49": {
        "name": "Business OSINT Report",
        "price": "$49",
        "mode": "payment",
        "category": "osint_report",
    },
    "price_property_osint_report_75": {
        "name": "Property OSINT Report",
        "price": "$75",
        "mode": "payment",
        "category": "osint_report",
    },
    "price_digital_footprint_report_99": {
        "name": "Digital Footprint Report",
        "price": "$99",
        "mode": "payment",
        "category": "osint_report",
    },
    "price_unlimited_osint_reports_199": {
        "name": "Unlimited OSINT Reports",
        "price": "$199/mo",
        "mode": "subscription",
        "category": "osint_report_subscription",
    },
    "price_scan_single_19": {
        "name": "OSINT + AI Enrichment Scan",
        "price": "$19",
        "mode": "payment",
        "category": "scan_credit",
        "quantity": 1,
    },
    "price_scan_pack_10_149": {
        "name": "10 OSINT + AI Enrichment Scans",
        "price": "$149",
        "mode": "payment",
        "category": "scan_credit",
        "quantity": 10,
    },
    "price_scan_pack_50_499": {
        "name": "50 OSINT + AI Enrichment Scans",
        "price": "$499",
        "mode": "payment",
        "category": "scan_credit",
        "quantity": 50,
    },
    "price_lead_intel_report_99": {
        "name": "Lead Intelligence Report",
        "price": "$99",
        "mode": "payment",
        "category": "lead_intelligence_report",
    },
    "price_unlimited_lead_intel_499": {
        "name": "Unlimited Lead Intelligence Reports",
        "price": "$499/mo",
        "mode": "subscription",
        "category": "lead_intelligence_subscription",
    },
    "price_lead_verify_batch_99": {
        "name": "Lead Verification + Enrichment Batch",
        "price": "$99",
        "mode": "payment",
        "category": "lead_verification",
        "quantity": 100,
    },
    "price_lead_verify_plan_99": {
        "name": "Lead Verification Starter Plan",
        "price": "$99/mo",
        "mode": "subscription",
        "category": "lead_verification_subscription",
    },
    "price_lead_verify_plan_299": {
        "name": "Lead Verification Growth Plan",
        "price": "$299/mo",
        "mode": "subscription",
        "category": "lead_verification_subscription",
    },
    "price_lead_verify_plan_499": {
        "name": "Lead Verification Agency Plan",
        "price": "$499/mo",
        "mode": "subscription",
        "category": "lead_verification_subscription",
    },
    "price_ai_outreach_199": {
        "name": "AI Outreach Intelligence Starter",
        "price": "$199/mo",
        "mode": "subscription",
        "category": "ai_sales_intelligence",
    },
    "price_ai_profiles_499": {
        "name": "AI Prospect Profiles Growth",
        "price": "$499/mo",
        "mode": "subscription",
        "category": "ai_sales_intelligence",
    },
    "price_ai_business_intel_999": {
        "name": "AI Business Intelligence Command",
        "price": "$999/mo",
        "mode": "subscription",
        "category": "ai_sales_intelligence",
    },
    "price_starter_350": {
        "name": "Starter Premium Lead Plan",
        "price": "$350/mo",
        "mode": "subscription",
        "category": "pricing_plan",
        "quantity": 10,
    },
    "price_pro_700": {
        "name": "Pro Premium Lead Plan",
        "price": "$700/mo",
        "mode": "subscription",
        "category": "pricing_plan",
        "quantity": 25,
    },
    "price_elite_1000": {
        "name": "Elite Premium Lead Plan",
        "price": "$1,000/mo",
        "mode": "subscription",
        "category": "pricing_plan",
        "quantity": 50,
    },
    "price_dfy_997": {
        "name": "DFY Lead Machine",
        "price": "$1,500 setup + $997/mo",
        "mode": "subscription",
        "category": "pricing_plan",
        "setupPriceId": "price_dfy_setup_1500",
    },
    "price_osint_basic": {
        "name": "Real Estate OSINT Report",
        "price": "$75",
        "mode": "payment",
        "category": "osint",
    },
    "price_osint_deep": {
        "name": "Deep OSINT Investigation",
        "price": "$150",
        "mode": "payment",
        "category": "osint",
    },
    "price_osint_homeowner": {
        "name": "Homeowner Identity Report",
        "price": "$99",
        "mode": "payment",
        "category": "osint",
    },
    "price_intel_market": {
        "name": "Real Estate Market Intelligence Report",
        "price": "$149",
        "mode": "payment",
        "category": "intelligence",
    },
    "price_intel_neighborhood": {
        "name": "Neighborhood Buyer Intent Report",
        "price": "$99",
        "mode": "payment",
        "category": "intelligence",
    },
    "price_intel_competitor": {
        "name": "Competitor Agent Activity Report",
        "price": "$79",
        "mode": "payment",
        "category": "intelligence",
    },
}


class LaunchHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/event":
            self.send_header("Access-Control-Allow-Origin", os.environ.get("TRACKING_ALLOWED_ORIGIN", "*"))
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", "86400")

        if parsed.path in {"", "/", "/index.html", "/dashboard.html", "/workflow-demo.html", "/workflow-demo.css", "/lead-control-center.html", "/static/lead-control-center.html"}:
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")

        super().end_headers()

    def do_OPTIONS(self) -> None:
        if urllib.parse.urlparse(self.path).path.rstrip("/") == "/api/event":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        self.send_response(HTTPStatus.NOT_FOUND)
        self.end_headers()

    def do_GET(self) -> None:
        if self.path.rstrip("/") in {"/health", "/healthz"}:
            self.send_json({"ok": True, "status": "ok", "service": "leadgen-launch-site"}, HTTPStatus.OK)
            return

        parsed = urllib.parse.urlparse(self.path)
        route = parsed.path.rstrip("/")
        if route == "/ready":
            self.handle_ready()
            return

        if route == "/metrics":
            self.handle_metrics()
            return

        if route == "/api/revenue-status":
            self.handle_revenue_status()
            return

        if route == "/api/fulfillment-status":
            self.handle_fulfillment_status()
            return

        if route == "/api/health":
            self.handle_api_health()
            return

        if route == "/api/scraper-queue":
            self.handle_scraper_queue()
            return

        if route == "/api/lead-stats":
            self.handle_lead_stats()
            return

        if route in {"/api/hubspot-status", "/api/crm-status"}:
            self.handle_hubspot_status()
            return

        if route in {"/api/chat-status", "/api/llama-status"}:
            self.handle_chat_status()
            return

        query = urllib.parse.parse_qs(parsed.query)
        if parsed.path in {"", "/"} and query.get("page", [""])[0] == "dashboard":
            self.path = "/dashboard.html"

        if parsed.path.rstrip("/") == "/dashboard":
            self.path = "/dashboard.html"

        if parsed.path.rstrip("/") == "/workflow-demo":
            self.path = "/workflow-demo.html"

        if parsed.path.rstrip("/") in {"/lead-control-center", "/control-center", "/control", "/static/lead-control-center.html"}:
            self.path = "/lead-control-center.html"

        self.apply_index_fallback()
        super().do_GET()

    def apply_index_fallback(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        requested_path = urllib.parse.unquote(parsed.path).lstrip("/")
        if not requested_path:
            return

        target = (ROOT / requested_path).resolve()
        try:
            target.relative_to(ROOT)
        except ValueError:
            self.path = "/index.html"
            return

        if not target.exists():
            self.path = "/index.html"

    def do_POST(self) -> None:
        route = urllib.parse.urlparse(self.path).path.rstrip("/")
        if route == "/api/chat":
            self.handle_chat()
            return

        if route == "/api/enrich-score":
            self.handle_enrich_score()
            return

        if route == "/api/sale-listing":
            self.handle_sale_listing()
            return

        if route == "/api/osint-report":
            self.handle_osint_report()
            return

        if route == "/api/revenue-status":
            self.handle_revenue_status()
            return

        if route == "/api/fulfillment-status":
            self.handle_fulfillment_status()
            return

        if route == "/api/event":
            self.handle_event()
            return

        if route == "/api/lead-package-request":
            self.handle_lead_package_request()
            return

        if route in {"/api/hubspot-export", "/api/crm-export"}:
            self.handle_hubspot_export()
            return

        if route == "/api/checkout":
            self.handle_checkout()
            return

        if route in {"/api/stripe-webhook", "/stripe/webhook"}:
            self.handle_stripe_webhook()
            return

        if route != "/api/waitlist":
            self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return

        try:
            payload = self.read_json_body()
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        email = str(payload.get("email", "")).strip().lower()
        company = str(payload.get("company", "")).strip()

        if not EMAIL_RE.match(email):
            self.send_json({"error": "Enter a valid email address."}, HTTPStatus.BAD_REQUEST)
            return

        record = {
            "email": email,
            "company": company,
            "source": "launch_site",
            "capturedAt": datetime.now(timezone.utc).isoformat(),
            "remoteAddress": self.client_address[0],
        }

        DATA_DIR.mkdir(exist_ok=True)
        with WAITLIST_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

        notification = self.try_send_resend_notification(record)
        self.send_json(
            {
                "ok": True,
                "message": "Pilot request received.",
                "notification": notification,
            },
            HTTPStatus.OK,
        )

    def handle_chat(self) -> None:
        try:
            payload = self.read_json_body()
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            self.send_json({"error": "Enter a message for Nexus AI."}, HTTPStatus.BAD_REQUEST)
            return

        if len(prompt) > 2000:
            self.send_json({"error": "Message is too long."}, HTTPStatus.BAD_REQUEST)
            return

        answer, mode = self.generate_chat_response(prompt)
        self.send_json(
            {
                "ok": True,
                "assistant": "Nexus Llama 3",
                "mode": mode,
                "answer": answer,
            },
            HTTPStatus.OK,
        )

    def handle_chat_status(self) -> None:
        self.send_json({"ok": True, "chat": self.chat_status()}, HTTPStatus.OK)

    def handle_enrich_score(self) -> None:
        try:
            payload = self.read_json_body()
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        lead = payload.get("lead")
        if not isinstance(lead, dict):
            self.send_json({"error": "Request requires a lead object."}, HTTPStatus.BAD_REQUEST)
            return

        result = self.enrich_and_score_lead(lead)
        self.send_json({"ok": True, "result": result}, HTTPStatus.OK)

    def handle_sale_listing(self) -> None:
        try:
            payload = self.read_json_body()
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        lead = payload.get("lead")
        if not isinstance(lead, dict):
            self.send_json({"error": "Request requires a lead object."}, HTTPStatus.BAD_REQUEST)
            return

        enriched = self.enrich_and_score_lead(lead)
        listing = self.create_sale_listing(enriched)
        self.send_json({"ok": True, "listing": listing}, HTTPStatus.OK)

    def handle_osint_report(self) -> None:
        try:
            payload = self.read_json_body()
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        report_type = str(payload.get("reportType", "")).strip().lower()
        subject = str(payload.get("subject", "")).strip()
        requester_email = str(payload.get("requesterEmail", "")).strip().lower()
        use_case = str(payload.get("useCase", "")).strip()
        scope_notes = str(payload.get("scopeNotes", "")).strip()
        public_urls = str(payload.get("publicUrls", "")).strip()
        authorized = bool(payload.get("authorized"))

        allowed_types = {
            "people": "Authorized People OSINT Report",
            "business": "Business OSINT Report",
            "property": "Property OSINT Report",
            "digital": "Digital Footprint Report",
        }
        if report_type not in allowed_types:
            self.send_json({"error": "Choose a valid OSINT report type."}, HTTPStatus.BAD_REQUEST)
            return

        if not subject or len(subject) > 160:
            self.send_json({"error": "Enter a report subject under 160 characters."}, HTTPStatus.BAD_REQUEST)
            return

        if not EMAIL_RE.match(requester_email):
            self.send_json({"error": "Enter a valid requester email."}, HTTPStatus.BAD_REQUEST)
            return

        if not authorized:
            self.send_json({"error": "Authorization confirmation is required before OSINT intake."}, HTTPStatus.BAD_REQUEST)
            return

        unsafe_text = " ".join([subject, use_case, scope_notes]).lower()
        blocked_terms = ("live location", "track phone", "phone location", "gps", "stalk", "password", "bypass", "hack")
        if any(term in unsafe_text for term in blocked_terms):
            self.send_json(
                {
                    "error": "This OSINT workflow only supports authorized public-source reporting. It cannot perform covert tracking, credential access, or number-only location lookup."
                },
                HTTPStatus.BAD_REQUEST,
            )
            return

        record = {
            "reportId": f"osint_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            "reportType": report_type,
            "reportName": allowed_types[report_type],
            "subject": subject,
            "requesterEmail": requester_email,
            "useCase": use_case or "Authorized public-source due diligence",
            "scopeNotes": scope_notes,
            "publicUrls": [item.strip() for item in public_urls.splitlines() if item.strip()][:8],
            "authorized": authorized,
            "status": "generated_safe_preview",
            "capturedAt": datetime.now(timezone.utc).isoformat(),
            "remoteAddress": self.client_address[0],
        }
        report = self.build_osint_report(record)
        record["report"] = report

        DATA_DIR.mkdir(exist_ok=True)
        with OSINT_REPORTS_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

        notification = self.try_send_osint_report_notification(record)
        self.send_json(
            {
                "ok": True,
                "message": "Authorized OSINT report preview generated and queued for review.",
                "notification": notification,
                "report": report,
            },
            HTTPStatus.OK,
        )

    def handle_revenue_status(self) -> None:
        self.send_json(
            {
                "ok": True,
                "resend": self.resend_status(),
                "stripe": self.stripe_status(),
                "leadMarket": self.hq_florida_market(),
            },
            HTTPStatus.OK,
        )

    def handle_api_health(self) -> None:
        self.send_json(
            {
                "ok": True,
                "status": "healthy",
                "service": "leadgen-launch-site",
                "health": "/health",
                "ready": "/ready",
                "metrics": "/metrics",
                "checkedAt": datetime.now(timezone.utc).isoformat(),
            },
            HTTPStatus.OK,
        )

    def handle_ready(self) -> None:
        payload = self.readiness_payload()
        status = HTTPStatus.OK if payload["ready"] else HTTPStatus.SERVICE_UNAVAILABLE
        self.send_json(payload, status)

    def handle_metrics(self) -> None:
        self.send_text(self.prometheus_metrics(), HTTPStatus.OK, "text/plain; version=0.0.4; charset=utf-8")

    def handle_scraper_queue(self) -> None:
        summary = self.load_json_file(SCRAPER_SUMMARY_PATH)
        errors = summary.get("errors", [])
        if not isinstance(errors, list):
            errors = []

        self.send_json(
            {
                "ok": True,
                "status": "Queue Idle",
                "queued": 0,
                "running": 0,
                "failedLast24h": len(errors),
                "lastRunAt": summary.get("last_run_at"),
                "source": summary.get("source", "No scraper summary available"),
            },
            HTTPStatus.OK,
        )

    def handle_lead_stats(self) -> None:
        summary = self.load_json_file(SCRAPER_SUMMARY_PATH)
        total = int(summary.get("total_records") or self.count_lines(SCRAPER_JSONL_PATH) or 0)
        last_run_at = str(summary.get("last_run_at") or "")
        new_records = int(summary.get("new_records") or 0)
        today = new_records if self.is_today(last_run_at) else 0
        week = total if self.is_within_days(last_run_at, 7) else 0

        self.send_json(
            {
                "ok": True,
                "today": today,
                "week": week,
                "total": total,
                "lastRunAt": last_run_at or None,
                "source": "scraper summary" if summary else "default",
                "quality": summary.get("quality") or {},
            },
            HTTPStatus.OK,
        )

    def handle_hubspot_status(self) -> None:
        self.send_json({"ok": True, "hubspot": self.hubspot_status()}, HTTPStatus.OK)

    def handle_hubspot_export(self) -> None:
        try:
            payload = self.read_json_body(max_length=32768)
        except ValueError as exc:
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        token = self.hubspot_access_token()
        if not token:
            self.send_json(
                {"ok": False, "error": "HubSpot is not configured.", "missing": self.hubspot_missing_token_names()},
                HTTPStatus.SERVICE_UNAVAILABLE,
            )
            return

        lead = payload.get("lead")
        if not isinstance(lead, dict):
            self.send_json({"ok": False, "error": "Request requires a lead object."}, HTTPStatus.BAD_REQUEST)
            return

        try:
            properties = self.hubspot_contact_properties(lead)
        except ValueError as exc:
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        try:
            result = self.upsert_hubspot_contact(token, properties)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            self.send_json(
                {
                    "ok": False,
                    "error": "HubSpot rejected the contact export.",
                    "status": exc.code,
                    "detail": detail[:1200],
                },
                HTTPStatus.BAD_GATEWAY,
            )
            return
        except Exception as exc:  # noqa: BLE001 - return safe CRM error to browser.
            self.send_json({"ok": False, "error": f"HubSpot export failed: {exc}"}, HTTPStatus.BAD_GATEWAY)
            return

        record = {
            "capturedAt": datetime.now(timezone.utc).isoformat(),
            "remoteAddress": self.client_address[0],
            "action": result["action"],
            "hubspotId": result["id"],
            "email": properties.get("email", ""),
            "company": properties.get("company", ""),
            "source": "nexus_hubspot_export",
        }
        DATA_DIR.mkdir(exist_ok=True)
        with HUBSPOT_EXPORTS_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

        self.send_json(
            {
                "ok": True,
                "message": f"HubSpot contact {result['action']}.",
                "hubspot": {"id": result["id"], "action": result["action"]},
                "properties": {key: value for key, value in properties.items() if key != "email"},
            },
            HTTPStatus.OK,
        )

    def handle_event(self) -> None:
        try:
            payload = self.read_json_body(max_length=32768)
            event = self.normalize_event_payload(payload)
        except ValueError as exc:
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        database_url = os.environ.get("DATABASE_URL", "").strip()
        if not database_url:
            self.send_json(
                {"ok": False, "error": "DATABASE_URL is not configured for event tracking."},
                HTTPStatus.SERVICE_UNAVAILABLE,
            )
            return

        try:
            saved = self.save_event(database_url, event)
        except Exception as exc:  # noqa: BLE001 - return a JSON error instead of dropping browser events silently.
            self.send_json({"ok": False, "error": f"Event save failed: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self.send_json({"ok": True, **saved}, HTTPStatus.CREATED)

    def handle_fulfillment_status(self) -> None:
        all_records = self.read_fulfillment_records()
        records = [record for record in all_records if not self.is_smoke_fulfillment_record(record)]
        test_records = [record for record in all_records if self.is_smoke_fulfillment_record(record)]
        total = len(records)
        delivered = sum(1 for record in records if record.get("status") == "delivered")
        pending = sum(1 for record in records if str(record.get("status", "")).startswith("pending"))
        manual = sum(1 for record in records if "manual" in str(record.get("status", "")))
        revenue_cents = sum(
            int(record.get("amountTotal") or 0)
            for record in records
            if record.get("paymentStatus") in {"paid", "no_payment_required"}
        )
        test_pending = sum(1 for record in test_records if str(record.get("status", "")).startswith("pending"))
        test_manual = sum(1 for record in test_records if "manual" in str(record.get("status", "")))
        test_revenue_cents = sum(
            int(record.get("amountTotal") or 0)
            for record in test_records
            if record.get("paymentStatus") in {"paid", "no_payment_required"}
        )

        recent = [self.fulfillment_record_summary(record) for record in records[-10:]]
        test_recent = [self.fulfillment_record_summary(record) for record in test_records[-10:]]

        self.send_json(
            {
                "ok": True,
                "resend": self.resend_status(),
                "stripe": self.stripe_status(),
                "summary": {
                    "total": total,
                    "delivered": delivered,
                    "pending": pending,
                    "manual": manual,
                    "revenue": self.format_amount(revenue_cents, "usd"),
                },
                "recent": list(reversed(recent)),
                "testSummary": {
                    "total": len(test_records),
                    "pending": test_pending,
                    "manual": test_manual,
                    "revenue": self.format_amount(test_revenue_cents, "usd"),
                },
                "testRecords": list(reversed(test_recent)),
            },
            HTTPStatus.OK,
        )

    def handle_lead_package_request(self) -> None:
        try:
            payload = self.read_json_body()
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        email = str(payload.get("email", "")).strip().lower()
        quantity = int(payload.get("quantity", 0) or 0)
        tier = next((item for item in HQ_FLORIDA_PRICING if item["quantity"] == quantity), None)

        if not EMAIL_RE.match(email):
            self.send_json({"error": "Enter a valid delivery email."}, HTTPStatus.BAD_REQUEST)
            return

        if tier is None:
            self.send_json({"error": "Choose a valid HQ Florida lead package."}, HTTPStatus.BAD_REQUEST)
            return

        record = {
            "email": email,
            "quantity": quantity,
            "price": tier["price"],
            "currency": "USD",
            "package": "HQ Florida leads",
            "status": "purchase_request_received",
            "capturedAt": datetime.now(timezone.utc).isoformat(),
            "remoteAddress": self.client_address[0],
        }

        DATA_DIR.mkdir(exist_ok=True)
        with LEAD_PACKAGE_REQUESTS_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

        notification = self.try_send_lead_package_notification(record)
        self.send_json(
            {
                "ok": True,
                "message": "HQ Florida lead package request received.",
                "request": {
                    "quantity": quantity,
                    "price": tier["price"],
                    "currency": "USD",
                    "deliveryEmail": email,
                },
                "notification": notification,
            },
            HTTPStatus.OK,
        )

    def handle_checkout(self) -> None:
        try:
            payload = self.read_json_body()
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        requested_price_id = str(payload.get("priceId", "")).strip()
        price_id = requested_price_id or str(os.environ.get("PRICE_ID", "")).strip()
        catalog_item = STRIPE_CATALOG.get(price_id)
        if not catalog_item:
            self.send_json(
                {
                    "error": "Unknown Stripe price ID.",
                    "setupNeeded": not requested_price_id,
                    "missing": ["PRICE_ID"] if not requested_price_id else [],
                },
                HTTPStatus.BAD_REQUEST,
            )
            return

        stripe_secret = os.environ.get("STRIPE_SECRET_KEY")
        if not self.valid_stripe_secret(stripe_secret):
            self.send_json(
                {
                    "error": "Stripe is not configured.",
                    "setupNeeded": True,
                    "missing": ["STRIPE_SECRET_KEY"],
                    "catalogItem": catalog_item,
                },
                HTTPStatus.SERVICE_UNAVAILABLE,
            )
            return

        try:
            import stripe
        except ImportError:
            self.send_json(
                {
                    "error": "Stripe SDK is not installed.",
                    "setupNeeded": True,
                    "missing": ["stripe Python package"],
                },
                HTTPStatus.SERVICE_UNAVAILABLE,
            )
            return

        try:
            public_base_url = self.public_base_url()
            self.configure_stripe(stripe, stripe_secret)
            line_items = [self.checkout_line_item(stripe, price_id, catalog_item)]
            setup_price_id = catalog_item.get("setupPriceId")
            if setup_price_id:
                setup_key = str(setup_price_id)
                setup_item = STRIPE_CATALOG.get(setup_key) or {
                    "name": f"{catalog_item['name']} setup",
                    "price": "$1,500",
                    "mode": "payment",
                    "category": str(catalog_item["category"]),
                }
                line_items.append(self.checkout_line_item(stripe, setup_key, setup_item))

            session = stripe.checkout.Session.create(
                mode=catalog_item["mode"],
                line_items=line_items,
                client_reference_id=price_id,
                metadata={
                    "nexus_price_id": price_id,
                    "nexus_catalog_name": str(catalog_item["name"]),
                    "nexus_catalog_category": str(catalog_item["category"]),
                },
                success_url=f"{public_base_url}/dashboard?checkout=success",
                cancel_url=f"{public_base_url}/dashboard?checkout=cancel",
            )
            self.send_json({"ok": True, "url": session.url, "catalogItem": catalog_item}, HTTPStatus.OK)
        except LookupError as exc:
            self.send_json({"error": str(exc), "catalogItem": catalog_item}, HTTPStatus.BAD_REQUEST)
        except ValueError as exc:
            self.send_json({"error": str(exc), "setupNeeded": True, "missing": ["PUBLIC_BASE_URL"]}, HTTPStatus.SERVICE_UNAVAILABLE)
        except Exception:  # noqa: BLE001 - return a safe payment error to the browser.
            self.send_json({"error": "Stripe checkout failed. Check server logs and Stripe configuration."}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def resolve_stripe_price_id(self, stripe: Any, price_key: str) -> str:
        try:
            price = stripe.Price.retrieve(price_key)
            if getattr(price, "id", None):
                return str(price.id)
        except Exception:  # noqa: BLE001 - fall through to lookup key search.
            pass

        prices = stripe.Price.list(lookup_keys=[price_key], active=True, limit=1)
        if getattr(prices, "data", None):
            return str(prices.data[0].id)

        raise LookupError(
            f"Stripe price is not configured for {price_key}. Create a Stripe Price with this lookup key or update the catalog with the real price ID."
        )

    def checkout_line_item(self, stripe: Any, price_key: str, catalog_item: dict[str, Any]) -> dict[str, Any]:
        try:
            return {"price": self.resolve_stripe_price_id(stripe, price_key), "quantity": 1}
        except LookupError:
            return {"price_data": self.catalog_price_data(price_key, catalog_item), "quantity": 1}

    def catalog_price_data(self, price_key: str, catalog_item: dict[str, Any]) -> dict[str, Any]:
        mode = str(catalog_item.get("mode") or "payment")
        price_data: dict[str, Any] = {
            "currency": "usd",
            "unit_amount": self.catalog_unit_amount(catalog_item, mode),
            "product_data": {
                "name": str(catalog_item["name"]),
                "metadata": {
                    "nexus_price_id": price_key,
                    "nexus_catalog_category": str(catalog_item["category"]),
                },
            },
        }
        if mode == "subscription":
            price_data["recurring"] = {"interval": "month"}
        return price_data

    def catalog_unit_amount(self, catalog_item: dict[str, Any], mode: str) -> int:
        price_text = str(catalog_item.get("price") or "")
        matches = re.findall(r"\$([\d,]+(?:\.\d{1,2})?)(/mo)?", price_text)
        if not matches:
            raise LookupError(f"Catalog item {catalog_item.get('name', 'unknown')} is missing a usable price.")

        selected = matches[0]
        if mode == "subscription":
            selected = next((match for match in reversed(matches) if match[1] == "/mo"), matches[-1])

        amount = float(selected[0].replace(",", ""))
        return int(round(amount * 100))

    def handle_stripe_webhook(self) -> None:
        webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
        stripe_secret = os.environ.get("STRIPE_SECRET_KEY")
        if not stripe_secret or not webhook_secret:
            missing = []
            if not stripe_secret:
                missing.append("STRIPE_SECRET_KEY")
            if not webhook_secret:
                missing.append("STRIPE_WEBHOOK_SECRET")
            self.send_json({"error": "Stripe webhook is not configured.", "missing": missing}, HTTPStatus.SERVICE_UNAVAILABLE)
            return

        try:
            payload = self.read_raw_body(max_length=65536)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        signature = self.headers.get("Stripe-Signature", "")
        try:
            import stripe

            self.configure_stripe(stripe, stripe_secret)
            event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
        except Exception:
            self.send_json({"error": "Invalid Stripe webhook signature."}, HTTPStatus.BAD_REQUEST)
            return

        event_type = self.object_value(event, "type", "")
        if event_type != "checkout.session.completed":
            self.send_json({"ok": True, "ignored": event_type}, HTTPStatus.OK)
            return

        session = self.object_value(self.object_value(event, "data", {}), "object", {})
        record = self.fulfill_checkout_session(session)
        self.send_json({"ok": True, "fulfillmentStatus": record["status"]}, HTTPStatus.OK)

    def fulfill_checkout_session(self, session: Any) -> dict[str, Any]:
        session_id = str(self.object_value(session, "id", "") or "")
        existing = self.latest_fulfillment_record(session_id)
        if existing:
            return existing

        metadata = self.object_to_dict(self.object_value(session, "metadata", {}) or {})
        price_id = str(metadata.get("nexus_price_id") or self.object_value(session, "client_reference_id", "") or "")
        catalog_item = STRIPE_CATALOG.get(price_id, {})
        buyer_email = self.checkout_buyer_email(session)
        payment_status = str(self.object_value(session, "payment_status", "") or "unknown")

        record = {
            "sessionId": session_id,
            "priceId": price_id,
            "catalogName": catalog_item.get("name") or metadata.get("nexus_catalog_name") or "Unknown Nexus purchase",
            "category": catalog_item.get("category") or metadata.get("nexus_catalog_category") or "unknown",
            "quantity": catalog_item.get("quantity"),
            "amountTotal": self.object_value(session, "amount_total"),
            "currency": self.object_value(session, "currency"),
            "paymentStatus": payment_status,
            "buyerEmail": buyer_email,
            "capturedAt": datetime.now(timezone.utc).isoformat(),
            "stripeMode": self.object_value(session, "mode"),
            "status": "received",
            "delivery": "not_started",
        }

        if payment_status not in {"paid", "no_payment_required"}:
            record["status"] = "payment_not_cleared"
            record["delivery"] = "blocked_until_payment_clears"
            self.append_fulfillment_record(record)
            return record

        if not buyer_email:
            record["status"] = "needs_manual_delivery_no_buyer_email"
            record["delivery"] = "manual_review"
            self.append_fulfillment_record(record)
            return record

        delivery_result = self.try_send_fulfillment_email(record)
        record["deliveryResult"] = delivery_result
        if delivery_result == "sent":
            record["status"] = "delivered"
            record["delivery"] = "email_sent"
        else:
            record["status"] = "pending_manual_delivery"
            record["delivery"] = "email_not_sent"

        self.append_fulfillment_record(record)
        return record

    def checkout_buyer_email(self, session: Any) -> str:
        customer_details = self.object_value(session, "customer_details", {}) or {}
        email = self.object_value(customer_details, "email", "") or self.object_value(session, "customer_email", "")
        return str(email or "").strip().lower()

    def latest_fulfillment_record(self, session_id: str) -> dict[str, Any] | None:
        if not session_id or not FULFILLMENT_EVENTS_PATH.exists():
            return None

        latest: dict[str, Any] | None = None
        with FULFILLMENT_EVENTS_PATH.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("sessionId") == session_id:
                    latest = record
        return latest

    def read_fulfillment_records(self) -> list[dict[str, Any]]:
        if not FULFILLMENT_EVENTS_PATH.exists():
            return []

        records: list[dict[str, Any]] = []
        with FULFILLMENT_EVENTS_PATH.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(record, dict):
                    records.append(record)
        return records

    def is_smoke_fulfillment_record(self, record: dict[str, Any]) -> bool:
        session_id = str(record.get("sessionId", "")).lower()
        buyer_email = str(record.get("buyerEmail", "")).lower()
        return "smoke" in session_id or buyer_email.endswith("@example.com")

    def fulfillment_record_summary(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "sessionId": str(record.get("sessionId", ""))[-10:],
            "catalogName": record.get("catalogName", "Unknown purchase"),
            "category": record.get("category", "unknown"),
            "quantity": record.get("quantity"),
            "status": record.get("status", "unknown"),
            "delivery": record.get("delivery", "unknown"),
            "deliveryResult": record.get("deliveryResult", ""),
            "buyerEmail": self.mask_email(str(record.get("buyerEmail", ""))),
            "capturedAt": record.get("capturedAt"),
            "amount": self.format_amount(record.get("amountTotal"), record.get("currency")),
        }

    def append_fulfillment_record(self, record: dict[str, Any]) -> None:
        DATA_DIR.mkdir(exist_ok=True)
        with FULFILLMENT_EVENTS_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def try_send_fulfillment_email(self, record: dict[str, Any]) -> str:
        if not self.resend_status()["configured"]:
            return "skipped: Resend delivery not configured"

        try:
            from html import escape

            import resend

            sender = self.resend_sender()
            notify_to = os.environ.get("WAITLIST_NOTIFY_TO") or os.environ["RESEND_TO"]
            buyer_email = str(record["buyerEmail"])
            resend.api_key = os.environ["RESEND_API_KEY"]

            safe_name = escape(str(record["catalogName"]))
            safe_email = escape(buyer_email)
            session_id = escape(str(record["sessionId"]))
            quantity = record.get("quantity")
            quantity_line = f"<p><strong>Lead quantity:</strong> {int(quantity)}</p>" if quantity else ""
            buyer_text_quantity = f"\nLead quantity: {int(quantity)}" if quantity else ""

            buyer_html = (
                "<h1>Nexus order confirmed</h1>"
                f"<p>Your payment for <strong>{safe_name}</strong> was received.</p>"
                f"{quantity_line}"
                f"<p><strong>Fulfillment ID:</strong> {session_id}</p>"
                "<p>Your delivery has been logged. If this is a lead bundle, the reviewed lead file must be connected "
                "to the fulfillment inventory before raw lead data can be sent automatically.</p>"
            )
            buyer_text = (
                "Nexus order confirmed\n"
                f"Product: {record['catalogName']}"
                f"{buyer_text_quantity}\n"
                f"Fulfillment ID: {record['sessionId']}\n"
                "Your delivery has been logged. If this is a lead bundle, connect the reviewed lead inventory for automatic raw lead-file delivery."
            )

            resend.Emails.send(
                {
                    "from": sender,
                    "to": [buyer_email],
                    "subject": f"Nexus order confirmed: {record['catalogName']}",
                    "html": buyer_html,
                    "text": buyer_text,
                }
            )

            if notify_to != buyer_email:
                resend.Emails.send(
                    {
                        "from": sender,
                        "to": [notify_to],
                        "subject": f"Paid Nexus order fulfilled: {record['catalogName']}",
                        "html": (
                            "<h1>Paid Nexus order</h1>"
                            f"<p><strong>Buyer:</strong> {safe_email}</p>"
                            f"<p><strong>Product:</strong> {safe_name}</p>"
                            f"{quantity_line}"
                            f"<p><strong>Stripe session:</strong> {session_id}</p>"
                        ),
                        "text": (
                            "Paid Nexus order\n"
                            f"Buyer: {buyer_email}\n"
                            f"Product: {record['catalogName']}"
                            f"{buyer_text_quantity}\n"
                            f"Stripe session: {record['sessionId']}"
                        ),
                    }
                )
            return "sent"
        except Exception as exc:  # noqa: BLE001 - Stripe should not keep retrying for email provider outages.
            return f"failed: {exc}"

    def object_value(self, value: Any, key: str, default: Any = None) -> Any:
        if isinstance(value, dict):
            return value.get(key, default)
        return getattr(value, key, default)

    def object_to_dict(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if hasattr(value, "to_dict_recursive"):
            return value.to_dict_recursive()
        if hasattr(value, "to_dict"):
            return value.to_dict()
        return {}

    def configure_stripe(self, stripe: Any, secret_key: str) -> None:
        stripe.api_key = secret_key
        stripe.api_version = STRIPE_API_VERSION

    def public_base_url(self) -> str:
        raw_url = (
            os.environ.get("PUBLIC_BASE_URL")
            or os.environ.get("CLOUDFLARE_TUNNEL_URL")
            or os.environ.get("CF_PAGES_URL")
            or "https://nexuscloud.sh"
        )
        url = raw_url.strip().rstrip("/")
        if not url.startswith(("https://", "http://")):
            raise ValueError("PUBLIC_BASE_URL or CLOUDFLARE_TUNNEL_URL must start with https:// or http://.")
        return url

    def mask_email(self, email: str) -> str:
        if "@" not in email:
            return ""
        local, domain = email.split("@", 1)
        if not local:
            return f"*@{domain}"
        return f"{local[:1]}***@{domain}"

    def format_amount(self, amount_cents: Any, currency: Any) -> str:
        try:
            cents = int(amount_cents or 0)
        except (TypeError, ValueError):
            cents = 0
        code = str(currency or "usd").upper()
        return f"${cents / 100:,.2f} {code}"

    def hubspot_status(self) -> dict[str, Any]:
        token_name, token = self.hubspot_token_source()
        portal_id = self.hubspot_portal_id()
        return {
            "configured": bool(token),
            "configuredBy": token_name if token else "",
            "portalIdConfigured": bool(portal_id),
            "portalId": portal_id,
            "embedScriptUrl": f"https://js-na2.hs-scripts.com/{portal_id}.js" if portal_id else "",
            "missing": [] if token else self.hubspot_missing_token_names(),
            "endpoint": "https://api.hubapi.com/crm/v3/objects/contacts",
        }

    def hubspot_access_token(self) -> str:
        return self.hubspot_token_source()[1]

    def hubspot_token_source(self) -> tuple[str, str]:
        for name in ("HUBSPOT_ACCESS_TOKEN", "HUBSPOT_SERVICE_KEY", "HUBSPOT_PRIVATE_APP_TOKEN", "HUBSPOT_API_KEY"):
            value = os.environ.get(name, "").strip()
            if value:
                return name, value
        return "", ""

    def hubspot_missing_token_names(self) -> list[str]:
        return ["HUBSPOT_ACCESS_TOKEN", "HUBSPOT_SERVICE_KEY", "HUBSPOT_PRIVATE_APP_TOKEN", "HUBSPOT_API_KEY"]

    def hubspot_portal_id(self) -> str:
        return os.environ.get("HUBSPOT_PORTAL_ID", "").strip() or HUBSPOT_DEFAULT_PORTAL_ID

    def hubspot_contact_properties(self, lead: dict[str, Any]) -> dict[str, str]:
        email = str(lead.get("email") or lead.get("enriched_email") or "").strip().lower()
        company = str(lead.get("company") or lead.get("name") or "").strip()
        full_name = str(lead.get("contactName") or lead.get("contact_name") or "").strip()
        first_name = str(lead.get("firstName") or lead.get("firstname") or "").strip()
        last_name = str(lead.get("lastName") or lead.get("lastname") or "").strip()
        if full_name and not first_name and not last_name:
            parts = full_name.split()
            first_name = parts[0]
            last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

        phone = str(lead.get("phone") or lead.get("enriched_phone") or "").strip()
        website = str(lead.get("website") or "").strip()
        city = str(lead.get("city") or "").strip()
        state = str(lead.get("state") or "").strip().upper()
        postcode = str(lead.get("postcode") or lead.get("zip") or "").strip()
        street = str(lead.get("street") or lead.get("address") or "").strip()

        if not any((email, phone, website, company)):
            raise ValueError("HubSpot export needs at least an email, phone, website, or company name.")
        if email and not EMAIL_RE.match(email):
            raise ValueError("HubSpot export email is invalid.")

        properties = {
            "email": email,
            "firstname": first_name,
            "lastname": last_name,
            "phone": phone,
            "company": company,
            "website": website,
            "city": city,
            "state": state,
            "zip": postcode,
            "address": street,
        }
        return {key: value for key, value in properties.items() if value}

    def upsert_hubspot_contact(self, token: str, properties: dict[str, str]) -> dict[str, str]:
        existing_id = self.find_hubspot_contact_by_email(token, properties.get("email", ""))
        if existing_id:
            response = self.hubspot_request(token, f"/crm/v3/objects/contacts/{existing_id}", {"properties": properties}, "PATCH")
            return {"id": str(response.get("id") or existing_id), "action": "updated"}

        response = self.hubspot_request(token, "/crm/v3/objects/contacts", {"properties": properties}, "POST")
        return {"id": str(response.get("id", "")), "action": "created"}

    def find_hubspot_contact_by_email(self, token: str, email: str) -> str:
        if not email:
            return ""
        payload = {
            "filterGroups": [
                {
                    "filters": [
                        {"propertyName": "email", "operator": "EQ", "value": email},
                    ],
                }
            ],
            "properties": ["email"],
            "limit": 1,
        }
        response = self.hubspot_request(token, "/crm/v3/objects/contacts/search", payload, "POST")
        results = response.get("results") if isinstance(response, dict) else []
        if isinstance(results, list) and results:
            return str(results[0].get("id") or "")
        return ""

    def hubspot_request(self, token: str, path: str, payload: dict[str, Any], method: str) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"https://api.hubapi.com{path}",
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method=method,
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}

    def read_json_body(self, max_length: int = 8192) -> dict[str, Any]:
        raw_body = self.read_raw_body(max_length=max_length)
        raw = raw_body.decode("utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be JSON.") from exc

        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def read_raw_body(self, max_length: int) -> bytes:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0 or length > max_length:
            raise ValueError("Invalid request body.")
        return self.rfile.read(length)

    def send_json(self, payload: dict[str, Any], status: HTTPStatus) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, payload: str, status: HTTPStatus, content_type: str) -> None:
        body = payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def normalize_event_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        event_name = str(payload.get("event_name") or "").strip()
        if event_name not in ALLOWED_EVENT_NAMES:
            allowed = ", ".join(sorted(ALLOWED_EVENT_NAMES))
            raise ValueError(f"event_name must be one of: {allowed}.")

        event_data = payload.get("event_data") or {}
        if not isinstance(event_data, dict):
            raise ValueError("event_data must be a JSON object when provided.")
        event_data = dict(event_data)

        visitor_id, external_visitor_id = self.uuid_or_external(payload.get("visitor_id"))
        lead_id, external_lead_id = self.uuid_or_external(payload.get("lead_id"))
        if external_visitor_id:
            event_data["external_visitor_id"] = external_visitor_id
        if external_lead_id:
            event_data["external_lead_id"] = external_lead_id

        return {
            "event_name": event_name,
            "client_id": self.clean_text(payload.get("client_id"), 256),
            "visitor_id": visitor_id,
            "lead_id": lead_id,
            "page_url": self.clean_text(payload.get("page_url"), 2048),
            "referrer": self.clean_text(payload.get("referrer"), 2048),
            "utm_source": self.clean_text(payload.get("utm_source"), 256),
            "utm_medium": self.clean_text(payload.get("utm_medium"), 256),
            "utm_campaign": self.clean_text(payload.get("utm_campaign"), 256),
            "utm_content": self.clean_text(payload.get("utm_content"), 256),
            "utm_term": self.clean_text(payload.get("utm_term"), 256),
            "gclid": self.clean_text(payload.get("gclid"), 512),
            "msclkid": self.clean_text(payload.get("msclkid"), 512),
            "fbclid": self.clean_text(payload.get("fbclid"), 512),
            "event_data": event_data,
        }

    def save_event(self, database_url: str, event: dict[str, Any]) -> dict[str, str]:
        import psycopg

        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cursor:
                visitor_id = self.resolve_visitor_id(cursor, event)
                cursor.execute(
                    """
                    INSERT INTO events (visitor_id, lead_id, event_name, page_url, event_data)
                    VALUES (%s, %s, %s, %s, %s::jsonb)
                    RETURNING id
                    """,
                    (
                        visitor_id,
                        self.resolve_lead_id(cursor, event),
                        event["event_name"],
                        event["page_url"],
                        json.dumps(event["event_data"], sort_keys=True),
                    ),
                )
                event_id = cursor.fetchone()[0]
        return {"event_id": str(event_id), "visitor_id": str(visitor_id)}

    def resolve_visitor_id(self, cursor: Any, event: dict[str, Any]) -> uuid.UUID:
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
            cursor.execute(
                "SELECT id FROM visitors WHERE client_id = %s ORDER BY last_seen_at DESC LIMIT 1",
                (event["client_id"],),
            )
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

    def resolve_lead_id(self, cursor: Any, event: dict[str, Any]) -> uuid.UUID | None:
        if not event["lead_id"]:
            return None
        cursor.execute("SELECT id FROM leads WHERE id = %s LIMIT 1", (event["lead_id"],))
        row = cursor.fetchone()
        if row:
            return row[0]
        event["event_data"]["unmatched_lead_id"] = str(event["lead_id"])
        return None

    def clean_text(self, value: Any, max_length: int) -> str:
        text = "" if value is None else str(value).strip()
        return text[:max_length]

    def uuid_or_external(self, value: Any) -> tuple[uuid.UUID | None, str]:
        text = self.clean_text(value, 256)
        if not text:
            return None, ""
        try:
            return uuid.UUID(text), ""
        except ValueError:
            return None, text

    def try_send_resend_notification(self, record: dict[str, Any]) -> str:
        if not os.environ.get("RESEND_API_KEY"):
            return "skipped: RESEND_API_KEY not configured"

        try:
            from html import escape

            import resend

            sender = self.resend_sender()
            notify_to = os.environ.get("WAITLIST_NOTIFY_TO") or os.environ["RESEND_TO"]
            resend.api_key = os.environ["RESEND_API_KEY"]

            safe_email = escape(record["email"])
            safe_company = escape(record.get("company", "") or "Not provided")

            resend.Emails.send(
                {
                    "from": sender,
                    "to": [notify_to],
                    "subject": "New LeadGen Virtual Hub pilot request",
                    "html": (
                        "<h1>New pilot request</h1>"
                        f"<p><strong>Email:</strong> {safe_email}</p>"
                        f"<p><strong>Company:</strong> {safe_company}</p>"
                        "<p><strong>Source:</strong> launch_site</p>"
                    ),
                    "text": (
                        "New pilot request\n"
                        f"Email: {record['email']}\n"
                        f"Company: {record.get('company', '') or 'Not provided'}\n"
                        "Source: launch_site"
                    ),
                }
            )
            return "sent"
        except Exception as exc:  # noqa: BLE001 - local server should not fail submission if email fails.
            return f"failed: {exc}"

    def try_send_lead_package_notification(self, record: dict[str, Any]) -> str:
        if not self.resend_status()["configured"]:
            return "skipped: Resend delivery not configured"

        try:
            from html import escape

            import resend

            sender = self.resend_sender()
            notify_to = os.environ.get("WAITLIST_NOTIFY_TO") or os.environ["RESEND_TO"]
            resend.api_key = os.environ["RESEND_API_KEY"]

            safe_email = escape(record["email"])
            quantity = int(record["quantity"])
            price = int(record["price"])
            resend.Emails.send(
                {
                    "from": sender,
                    "to": [notify_to],
                    "subject": f"HQ Florida lead package request: {quantity} leads",
                    "html": (
                        "<h1>HQ Florida lead package request</h1>"
                        f"<p><strong>Buyer email:</strong> {safe_email}</p>"
                        f"<p><strong>Package:</strong> {quantity} HQ Florida leads</p>"
                        f"<p><strong>Price:</strong> ${price} USD</p>"
                    ),
                    "text": (
                        "HQ Florida lead package request\n"
                        f"Buyer email: {record['email']}\n"
                        f"Package: {quantity} HQ Florida leads\n"
                        f"Price: ${price} USD"
                    ),
                }
            )
            return "sent"
        except Exception as exc:  # noqa: BLE001 - request storage should still succeed if email fails.
            return f"failed: {exc}"

    def generate_chat_response(self, prompt: str) -> tuple[str, str]:
        endpoint = self.llama_chat_endpoint()
        model = self.llama_chat_model()

        if endpoint:
            try:
                answer = self.call_llama_endpoint(endpoint, model, prompt)
                return answer, "llama_endpoint"
            except Exception as exc:  # noqa: BLE001 - fallback keeps the command center responsive.
                return (
                    f"Llama endpoint failed, so I am using safe mode. Error: {exc}. "
                    + self.safe_chat_response(prompt),
                    "safe_fallback",
                )

        return self.safe_chat_response(prompt), "safe_mode"

    def chat_status(self) -> dict[str, Any]:
        endpoint_name, endpoint = self.llama_endpoint_source()
        api_key_name, api_key = self.llama_api_key_source()
        return {
            "configured": bool(endpoint),
            "configuredBy": endpoint_name if endpoint else "",
            "model": self.llama_chat_model(),
            "authConfigured": bool(api_key),
            "authConfiguredBy": api_key_name if api_key else "",
            "missing": [] if endpoint else ["LLAMA_CHAT_ENDPOINT", "LLAMA3_CHAT_ENDPOINT", "OLLAMA_HOST"],
            "mode": "llama_endpoint" if endpoint else "safe_mode",
        }

    def llama_chat_model(self) -> str:
        return (
            os.environ.get("LLAMA_CHAT_MODEL")
            or os.environ.get("LLAMA3_CHAT_MODEL")
            or os.environ.get("OLLAMA_MODEL")
            or "llama3"
        ).strip()

    def llama_chat_endpoint(self) -> str:
        return self.llama_endpoint_source()[1]

    def llama_endpoint_source(self) -> tuple[str, str]:
        for name in ("LLAMA_CHAT_ENDPOINT", "LLAMA3_CHAT_ENDPOINT"):
            value = os.environ.get(name, "").strip()
            if value:
                return name, value
        ollama_host = os.environ.get("OLLAMA_HOST", "").strip().rstrip("/")
        if ollama_host:
            return "OLLAMA_HOST", f"{ollama_host}/api/chat"
        return "", ""

    def llama_api_key_source(self) -> tuple[str, str]:
        for name in ("LLAMA_CHAT_API_KEY", "LLAMA_API_KEY", "LLAMA3_API_KEY"):
            value = os.environ.get(name, "").strip()
            if value:
                return name, value
        return "", ""

    def call_llama_endpoint(self, endpoint: str, model: str, prompt: str) -> str:
        payload = {
            "model": model,
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Nexus Llama 3, a defensive lead-generation and operations assistant. "
                        "Help with leads, scraper health, storefront drafts, onsite privacy checks, and SaaS launch operations. "
                        "Do not help with covert tracking, credential theft, bypassing access controls, or unsafe surveillance."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        _, api_key = self.llama_api_key_source()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        request = urllib.request.Request(
            endpoint,
            data=body,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read().decode("utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            if isinstance(data.get("message"), dict) and data["message"].get("content"):
                return str(data["message"]["content"]).strip()
            choices = data.get("choices")
            if isinstance(choices, list) and choices:
                first = choices[0]
                if isinstance(first, dict):
                    message = first.get("message")
                    if isinstance(message, dict) and message.get("content"):
                        return str(message["content"]).strip()
                    if first.get("text"):
                        return str(first["text"]).strip()
            if data.get("response"):
                return str(data["response"]).strip()
        raise RuntimeError("Llama endpoint returned an unsupported response format")

    def safe_chat_response(self, prompt: str) -> str:
        lowered = prompt.lower()
        if "scraper" in lowered or "scrape" in lowered:
            return (
                "Scraper command view: check collector uptime, source allowlist, ingestion queue, "
                "dedupe rate, error spikes, and emergency stop status. Keep sources documented and rate-limited."
            )
        if "lead" in lowered:
            return (
                "Lead workflow: import, validate, dedupe, enrich, score, review, then create a sanitized storefront draft. "
                "Do not publish private contact fields by default."
            )
        if "onsite" in lowered or "room" in lowered or "camera" in lowered:
            return (
                "Onsite workflow: run the room privacy checklist, record authorized findings, label suspicious signals for review, "
                "and escalate through hotel/security or law enforcement when appropriate."
            )
        if "storefront" in lowered or "publish" in lowered:
            return (
                "Storefront workflow: create listing drafts first, exclude private notes and raw contact data, then publish only when "
                "score, privacy, and approval rules pass."
            )
        if "pi" in lowered:
            return (
                "Pi Suite workflow: register the field node, verify identity, run approved edge tasks, buffer offline data, "
                "and sync back to Nexus with audit logs."
            )
        return (
            "Nexus safe mode is online. I can help with lead workflows, 24/7 scraper operations, Pi Suite edge nodes, "
            "onsite privacy checks, storefront drafts, and launch readiness."
        )

    def enrich_and_score_lead(self, lead: dict[str, Any]) -> dict[str, Any]:
        company = str(lead.get("company") or "Unknown lead").strip()
        signal = str(lead.get("signal") or "").strip()
        market = str(lead.get("market") or "").strip()
        source = str(lead.get("source") or "approved source").strip()

        score = 52
        reasons: list[str] = []

        growth_terms = ("hiring", "growth", "expansion", "contract", "funding", "grant", "procurement")
        if any(term in signal.lower() for term in growth_terms):
            score += 24
            reasons.append("Strong buying or growth signal found after scrape.")

        if any(term in market.lower() for term in ("gov", "field", "security", "operations", "saas")):
            score += 14
            reasons.append("Market aligns with Nexus target segments.")

        if "approved" in source.lower() or "allowlist" in source.lower():
            score += 6
            reasons.append("Source is documented in the scraper allowlist.")

        score = max(0, min(score, 98))
        band = "High" if score >= 80 else "Medium" if score >= 60 else "Low"
        confidence = "High" if len(reasons) >= 3 else "Medium" if reasons else "Low"

        return {
            "company": company,
            "summary": (
                f"{company} appears to be a {market or 'target'} lead with scrape signal: "
                f"{signal or 'no signal provided'}."
            ),
            "score": score,
            "scoreBand": band,
            "confidence": confidence,
            "reasons": reasons or ["Insufficient signals; route to review before outreach."],
            "nextAction": "Create storefront draft" if score >= 80 else "Review enrichment" if score >= 60 else "Hold for more data",
            "storefrontSafeFields": {
                "title": company,
                "category": market or "Lead intelligence",
                "summary": f"{company} matched {band.lower()} priority criteria after enrichment.",
            },
        }

    def create_sale_listing(self, enriched: dict[str, Any]) -> dict[str, Any]:
        score = int(enriched["score"])
        market = self.hq_florida_market()
        return {
            "title": "HQ Florida - AI-enriched business lead packages",
            "category": enriched["storefrontSafeFields"]["category"],
            "summary": (
                f"{market['availableCount']} HQ Florida leads are staged for sale as reviewed, "
                "AI-enriched, storefront-safe packages."
            ),
            "score": score,
            "scoreBand": enriched["scoreBand"],
            "confidence": enriched["confidence"],
            "price": market["pricing"][0]["price"],
            "currency": "USD",
            "inventory": market,
            "pricing": market["pricing"],
            "included": [
                "AI enrichment summary",
                "Lead score and reasons",
                "Source type and provenance notes",
                "Suggested next action",
                "Storefront-safe company profile",
            ],
            "privateFieldsExcluded": [
                "Raw phone/email",
                "Internal notes",
                "Sensitive identifiers",
                "Unreviewed personal data",
            ],
            "cta": "Request this lead package",
            "status": "For Sale",
        }

    def build_osint_report(self, record: dict[str, Any]) -> dict[str, Any]:
        report_type = str(record["reportType"])
        subject = str(record["subject"])
        source_count = len(record.get("publicUrls") or [])
        base_score = {
            "people": 62,
            "business": 74,
            "property": 70,
            "digital": 68,
        }.get(report_type, 60)
        score = min(96, base_score + (source_count * 3))

        source_plan = [
            "Confirm subject identity from buyer-provided public context.",
            "Review public web, business, property, and reputation sources where applicable.",
            "Record source notes, timestamps, and confidence level for every finding.",
            "Exclude private credentials, private accounts, sensitive identifiers, and unverified personal data.",
        ]
        if report_type == "people":
            focus = ["authorized identity context", "public affiliation signals", "risk notes", "source confidence"]
        elif report_type == "business":
            focus = ["business identity", "web footprint", "reputation signals", "opportunity context"]
        elif report_type == "property":
            focus = ["property context", "public ownership/entity trail", "local signals", "review flags"]
        else:
            focus = ["public web footprint", "brand consistency", "reputation signals", "risk summary"]

        return {
            "reportId": record["reportId"],
            "title": f"{record['reportName']}: {subject}",
            "subject": subject,
            "status": "Safe preview generated",
            "confidence": "High" if source_count >= 3 else "Medium" if source_count else "Review required",
            "opportunityScore": score,
            "summary": (
                f"Nexus generated an authorized public-source OSINT preview for {subject}. "
                "The report is queued for analyst review before any customer delivery."
            ),
            "focusAreas": focus,
            "sourcePlan": source_plan,
            "providedSources": record.get("publicUrls") or [],
            "buyerSafeRules": [
                "Use only lawful public-source material and buyer-provided context.",
                "Do not perform covert tracking, account access, credential collection, or number-only location lookup.",
                "Mask sensitive personal data and route uncertain findings to manual review.",
                "Deliver a reviewed summary, source notes, confidence level, and recommended next action.",
            ],
            "nextAction": "Review sources and prepare customer-ready PDF/report delivery.",
        }

    def try_send_osint_report_notification(self, record: dict[str, Any]) -> str:
        if not self.resend_status()["configured"]:
            return "skipped: Resend delivery not configured"

        try:
            from html import escape

            import resend

            sender = self.resend_sender()
            notify_to = os.environ.get("WAITLIST_NOTIFY_TO") or os.environ["RESEND_TO"]
            resend.api_key = os.environ["RESEND_API_KEY"]

            report = record["report"]
            html = (
                "<h1>Nexus OSINT report queued</h1>"
                f"<p><strong>Report:</strong> {escape(str(report['title']))}</p>"
                f"<p><strong>Requester:</strong> {escape(str(record['requesterEmail']))}</p>"
                f"<p><strong>Use case:</strong> {escape(str(record['useCase']))}</p>"
                f"<p><strong>Status:</strong> {escape(str(report['status']))}</p>"
                f"<p><strong>Next action:</strong> {escape(str(report['nextAction']))}</p>"
            )
            text = (
                "Nexus OSINT report queued\n"
                f"Report: {report['title']}\n"
                f"Requester: {record['requesterEmail']}\n"
                f"Use case: {record['useCase']}\n"
                f"Status: {report['status']}\n"
                f"Next action: {report['nextAction']}"
            )
            resend.Emails.send(
                {
                    "from": sender,
                    "to": [notify_to],
                    "subject": f"Nexus OSINT queued: {record['reportName']}",
                    "html": html,
                    "text": text,
                }
            )
            return "sent"
        except Exception as exc:  # noqa: BLE001 - report queue should still persist if email fails.
            return f"failed: {exc}"

    def hq_florida_market(self) -> dict[str, Any]:
        return {
            "name": "HQ Florida leads",
            "region": "Florida",
            "segment": "HQ business leads",
            "availableCount": HQ_FLORIDA_LEAD_COUNT,
            "status": "For Sale",
            "pricing": [
                {"quantity": tier["quantity"], "price": tier["price"], "priceId": tier["priceId"], "currency": "USD"}
                for tier in HQ_FLORIDA_PRICING
            ],
            "delivery": "Delivered after purchase approval through configured Resend email workflow.",
            "privacy": "Public listing excludes raw phone/email, sensitive identifiers, and unreviewed personal data.",
        }

    def resend_status(self) -> dict[str, Any]:
        sender = self.resend_sender()
        required = {
            "RESEND_API_KEY": os.environ.get("RESEND_API_KEY"),
            "RESEND_FROM or EMAIL_DOMAIN": sender,
            "WAITLIST_NOTIFY_TO or RESEND_TO": os.environ.get("WAITLIST_NOTIFY_TO") or os.environ.get("RESEND_TO"),
        }
        missing = [name for name, value in required.items() if not value]
        return {
            "configured": not missing,
            "missing": missing,
            "sender": sender,
            "message": "Resend delivery is configured." if not missing else "Resend delivery needs production email secrets.",
        }

    def resend_sender(self) -> str:
        explicit_sender = os.environ.get("RESEND_FROM", "").strip()
        if explicit_sender:
            return explicit_sender

        email_domain = os.environ.get("EMAIL_DOMAIN", "").strip()
        if email_domain:
            return f"NEXUS <no-reply@{email_domain}>"

        return ""

    def stripe_status(self) -> dict[str, Any]:
        public_url_error = ""
        try:
            public_base_url = self.public_base_url()
        except ValueError as exc:
            public_base_url = ""
            public_url_error = str(exc)

        required = {
            "STRIPE_SECRET_KEY": self.valid_stripe_secret(os.environ.get("STRIPE_SECRET_KEY")),
            "STRIPE_WEBHOOK_SECRET": bool(os.environ.get("STRIPE_WEBHOOK_SECRET")),
            "PUBLIC_BASE_URL": bool(public_base_url),
        }
        missing = [name for name, ready in required.items() if not ready]
        return {
            "configured": not missing,
            "missing": missing,
            "apiVersion": STRIPE_API_VERSION,
            "publicBaseUrl": public_base_url,
            "publicBaseUrlError": public_url_error,
            "catalogCount": len(STRIPE_CATALOG),
            "message": "Stripe checkout is configured." if not missing else "Stripe checkout needs production payment secrets.",
        }

    def valid_stripe_secret(self, value: str | None) -> bool:
        if not value:
            return False
        lowered = value.lower()
        if any(token in lowered for token in ("your_new", "paste", "rotated", "key_here", "xxxxxxxx")):
            return False
        return value.startswith(("sk_live_", "sk_test_")) and len(value) > 80

    def load_json_file(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def count_lines(self, path: Path) -> int:
        if not path.exists():
            return 0
        try:
            with path.open("r", encoding="utf-8") as handle:
                return sum(1 for _ in handle)
        except OSError:
            return 0

    def readiness_payload(self) -> dict[str, Any]:
        environment = os.environ.get("ENVIRONMENT", "development").strip().lower()
        data_dir_ready = self.ensure_data_dir_ready()
        required_config = {
            "databaseUrlConfigured": bool(os.environ.get("DATABASE_URL", "").strip()),
            "stripeConfigured": self.stripe_configured(),
            "resendConfigured": self.resend_status()["configured"],
            "hubspotConfigured": self.hubspot_status()["configured"],
        }
        production = environment == "production"
        config_ready = all(required_config.values()) if production else True
        ready = data_dir_ready and config_ready
        return {
            "ok": ready,
            "ready": ready,
            "status": "ready" if ready else "not_ready",
            "service": "leadgen-launch-site",
            "environment": environment,
            "checkedAt": datetime.now(timezone.utc).isoformat(),
            "checks": {
                "dataDirWritable": data_dir_ready,
                "requiredConfiguration": required_config,
                "productionConfigurationEnforced": production,
            },
        }

    def ensure_data_dir_ready(self) -> bool:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            SCRAPER_DIR.mkdir(parents=True, exist_ok=True)
        except OSError:
            return False
        return DATA_DIR.exists() and SCRAPER_DIR.exists()

    def prometheus_metrics(self) -> str:
        summary = self.load_json_file(SCRAPER_SUMMARY_PATH)
        readiness = self.readiness_payload()
        errors = summary.get("errors", [])
        if not isinstance(errors, list):
            errors = []
        quality = summary.get("quality") if isinstance(summary.get("quality"), dict) else {}
        last_run = self.parse_datetime(str(summary.get("last_run_at") or ""))
        last_run_timestamp = int(last_run.timestamp()) if last_run else 0
        lines = [
            "# HELP nexus_service_up Whether the Nexus launch server process is serving requests.",
            "# TYPE nexus_service_up gauge",
            'nexus_service_up{service="leadgen-launch-site"} 1',
            "# HELP nexus_service_ready Whether the Nexus launch server readiness check is passing.",
            "# TYPE nexus_service_ready gauge",
            f'nexus_service_ready{{service="leadgen-launch-site"}} {1 if readiness["ready"] else 0}',
            "# HELP nexus_scraper_total_records Total public-source OSINT records in the latest worker summary.",
            "# TYPE nexus_scraper_total_records gauge",
            f'nexus_scraper_total_records {int(summary.get("total_records") or self.count_lines(SCRAPER_JSONL_PATH) or 0)}',
            "# HELP nexus_scraper_new_records New public-source OSINT records collected in the latest run.",
            "# TYPE nexus_scraper_new_records gauge",
            f'nexus_scraper_new_records {int(summary.get("new_records") or 0)}',
            "# HELP nexus_scraper_failed_runs Failed source runs in the latest worker summary.",
            "# TYPE nexus_scraper_failed_runs gauge",
            f"nexus_scraper_failed_runs {len(errors)}",
            "# HELP nexus_scraper_last_run_timestamp_seconds Unix timestamp of the latest OSINT worker run.",
            "# TYPE nexus_scraper_last_run_timestamp_seconds gauge",
            f"nexus_scraper_last_run_timestamp_seconds {last_run_timestamp}",
        ]
        for status in ("approved_for_package", "review_recommended", "hold_for_manual_review"):
            lines.append(f'nexus_scraper_quality_records{{status="{status}"}} {int(quality.get(status) or 0)}')
        return "\n".join(lines) + "\n"

    def parse_datetime(self, value: str) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    def is_today(self, value: str) -> bool:
        parsed = self.parse_datetime(value)
        if parsed is None:
            return False
        return parsed.astimezone(timezone.utc).date() == datetime.now(timezone.utc).date()

    def is_within_days(self, value: str, days: int) -> bool:
        parsed = self.parse_datetime(value)
        if parsed is None:
            return False
        age = datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)
        return 0 <= age.total_seconds() <= days * 24 * 60 * 60


def main() -> int:
    host = os.environ.get("LAUNCH_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT") or os.environ.get("LAUNCH_PORT", "4173"))
    server = ThreadingHTTPServer((host, port), LaunchHandler)
    print(f"LeadGen Virtual Hub launch server running at http://{host}:{port}/")
    print(f"Waitlist submissions will be stored at {WAITLIST_PATH}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
