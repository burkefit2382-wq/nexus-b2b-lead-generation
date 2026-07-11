import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
HUBSPOT_TOKEN_NAMES = (
    "HUBSPOT_PRIVATE_APP_TOKEN",
    "HUBSPOT_ACCESS_TOKEN",
    "HUBSPOT_SERVICE_KEY",
    "HUBSPOT_API_KEY",
)
logger = logging.getLogger(__name__)


class HubSpotExportError(Exception):
    def __init__(self, message: str, status: int = 502, detail: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.detail = detail


def hubspot_status() -> dict[str, Any]:
    token_name, token = hubspot_token_source()
    portal_id = os.environ.get("HUBSPOT_PORTAL_ID", "").strip()
    return {
        "configured": bool(token),
        "configuredBy": token_name if token else "",
        "canonicalTokenName": HUBSPOT_TOKEN_NAMES[0],
        "portalIdConfigured": bool(portal_id),
        "missing": [] if token else hubspot_missing_token_names(),
        "endpoint": "https://api.hubapi.com/crm/v3/objects/contacts",
        "message": (
            "HubSpot private app token is configured."
            if token_name == HUBSPOT_TOKEN_NAMES[0]
            else "HubSpot is configured through a legacy token name; migrate to HUBSPOT_PRIVATE_APP_TOKEN."
            if token
            else "HubSpot is not configured."
        ),
    }


def hubspot_access_token() -> str:
    return hubspot_token_source()[1]


def hubspot_token_source() -> tuple[str, str]:
    for name in HUBSPOT_TOKEN_NAMES:
        value = os.environ.get(name, "").strip()
        if value:
            return name, value
    return "", ""


def hubspot_missing_token_names() -> list[str]:
    return list(HUBSPOT_TOKEN_NAMES)


def hubspot_contact_properties(lead: dict[str, Any]) -> dict[str, str]:
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


def upsert_hubspot_contact(token: str, properties: dict[str, str]) -> dict[str, str]:
    existing_id = find_hubspot_contact_by_email(token, properties.get("email", ""))
    if existing_id:
        response = hubspot_request(token, f"/crm/v3/objects/contacts/{existing_id}", {"properties": properties}, "PATCH")
        return {"id": str(response.get("id") or existing_id), "action": "updated"}

    response = hubspot_request(token, "/crm/v3/objects/contacts", {"properties": properties}, "POST")
    return {"id": str(response.get("id", "")), "action": "created"}


def find_hubspot_contact_by_email(token: str, email: str) -> str:
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
    response = hubspot_request(token, "/crm/v3/objects/contacts/search", payload, "POST")
    results = response.get("results") if isinstance(response, dict) else []
    if isinstance(results, list) and results:
        return str(results[0].get("id") or "")
    return ""


def hubspot_request(token: str, path: str, payload: dict[str, Any], method: str) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.hubapi.com{path}",
        data=body,
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "User-Agent": "NexusLeadGen/1.0 HubSpot CRM sync",
        },
        method=method,
    )
    max_attempts = hubspot_max_attempts()
    for attempt in range(1, max_attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if should_retry_hubspot_request(exc.code) and attempt < max_attempts:
                logger.warning(
                    "HubSpot request retrying after HTTP %s on attempt %s/%s for %s",
                    exc.code,
                    attempt,
                    max_attempts,
                    path,
                )
                time.sleep(hubspot_retry_delay_seconds(attempt, exc.headers.get("Retry-After")))
                continue
            raise HubSpotExportError(
                "HubSpot rejected the contact export.",
                status=exc.code,
                detail=detail[:1200],
            ) from exc
        except urllib.error.URLError as exc:
            if attempt < max_attempts:
                logger.warning(
                    "HubSpot request retrying after network failure on attempt %s/%s for %s: %s",
                    attempt,
                    max_attempts,
                    path,
                    exc.reason,
                )
                time.sleep(hubspot_retry_delay_seconds(attempt))
                continue
            raise HubSpotExportError(f"HubSpot export failed: {exc.reason}") from exc
    raise HubSpotExportError("HubSpot export failed after exhausting retries.")


def hubspot_max_attempts() -> int:
    raw_value = os.environ.get("HUBSPOT_MAX_RETRIES", "3").strip()
    try:
        return max(1, min(int(raw_value), 6))
    except ValueError:
        return 3


def should_retry_hubspot_request(status_code: int) -> bool:
    return status_code == 429 or 500 <= status_code <= 599


def hubspot_retry_delay_seconds(attempt: int, retry_after: str | None = None) -> float:
    if retry_after:
        try:
            return max(0.5, min(float(retry_after), 30.0))
        except ValueError:
            pass
    return min(0.5 * (2 ** (attempt - 1)), 8.0)
