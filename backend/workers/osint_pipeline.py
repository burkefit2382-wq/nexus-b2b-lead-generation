"""Deterministic, buyer-safe post-collection pipeline for public business OSINT."""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


PIPELINE_VERSION = "1.0"
ALLOWED_SOURCES = {"OpenStreetMap Overpass public data"}
PROHIBITED_FIELDS = {
    "date_of_birth",
    "dob",
    "password",
    "private_email",
    "social_security_number",
    "ssn",
}
PHONE_DIGITS_RE = re.compile(r"\D+")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def truthy_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def positive_int_env(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def normalize_website(value: Any) -> str:
    website = normalize_text(value)
    if not website:
        return ""
    parsed = urllib.parse.urlparse(website if "://" in website else f"https://{website}")
    host = parsed.netloc.lower().removeprefix("www.")
    if not host:
        return ""
    path = parsed.path.rstrip("/")
    return f"https://{host}{path}"


def normalize_phone(value: Any) -> str:
    digits = PHONE_DIGITS_RE.sub("", normalize_text(value))
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return f"+{digits}" if digits else ""


def canonical_identity(record: dict[str, Any]) -> str:
    website = normalize_website(record.get("website"))
    host = urllib.parse.urlparse(website).netloc if website else ""
    phone = normalize_phone(record.get("phone"))
    if host:
        basis = f"domain:{host}"
    elif phone:
        basis = f"phone:{phone}"
    else:
        basis = "|".join(
            [
                normalize_text(record.get("name")).casefold(),
                normalize_text(record.get("street")).casefold(),
                normalize_text(record.get("city")).casefold(),
                normalize_text(record.get("state")).upper(),
            ]
        )
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:20]


def normalize_record(record: dict[str, Any], retention_days: int) -> dict[str, Any]:
    normalized = dict(record)
    for field in ("name", "category", "county", "city", "postcode", "street", "source", "source_id"):
        normalized[field] = normalize_text(normalized.get(field))
    normalized["state"] = normalize_text(normalized.get("state")).upper()
    normalized["website"] = normalize_website(normalized.get("website"))
    normalized["phone"] = normalize_phone(normalized.get("phone"))
    normalized["canonical_id"] = canonical_identity(normalized)
    normalized["pipeline_version"] = PIPELINE_VERSION
    collected = parse_datetime(normalize_text(normalized.get("collected_at"))) or datetime.now(timezone.utc)
    normalized["retention_expires_at"] = (collected + timedelta(days=max(retention_days, 1))).isoformat()
    return normalized


def parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def load_suppression_values(path: Path) -> set[str]:
    values: set[str] = set()
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            item = line
        if isinstance(item, dict):
            candidates = [item.get("value"), item.get("canonical_id"), item.get("lead_id")]
            phone = normalize_phone(item.get("phone"))
            website = normalize_website(item.get("website"))
            candidates.extend([phone, website])
        else:
            candidates = [item]
        for candidate in candidates:
            value = normalize_text(candidate).casefold()
            if value:
                values.add(value)
    return values


def compliance_result(record: dict[str, Any], suppression_values: set[str]) -> dict[str, Any]:
    reasons: list[str] = []
    source = normalize_text(record.get("source"))
    if source not in ALLOWED_SOURCES:
        reasons.append("source_not_allowlisted")
    if any(field in record and normalize_text(record.get(field)) for field in PROHIBITED_FIELDS):
        reasons.append("prohibited_personal_data")
    subject_type = normalize_text(record.get("subject_type") or "business").casefold()
    if subject_type not in {"business", "organization", "public_location"}:
        reasons.append("unsupported_subject_type")
    candidates = {
        normalize_text(record.get("lead_id")).casefold(),
        normalize_text(record.get("canonical_id")).casefold(),
        normalize_text(record.get("phone")).casefold(),
        normalize_text(record.get("website")).casefold(),
    }
    if any(candidate and candidate in suppression_values for candidate in candidates):
        reasons.append("suppression_match")
    return {"allowed": not reasons, "reasons": sorted(set(reasons))}


def merge_records(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    preferred, fallback = (incoming, existing) if int(incoming.get("osint_quality_score") or 0) >= int(existing.get("osint_quality_score") or 0) else (existing, incoming)
    merged = dict(fallback)
    merged.update({key: value for key, value in preferred.items() if value not in (None, "", [])})
    source_ids = {
        normalize_text(item)
        for item in (
            existing.get("source_id"),
            incoming.get("source_id"),
            *(existing.get("source_ids") or []),
            *(incoming.get("source_ids") or []),
        )
        if normalize_text(item)
    }
    merged["source_ids"] = sorted(source_ids)
    merged["duplicate_count"] = int(existing.get("duplicate_count") or 1) + int(incoming.get("duplicate_count") or 1)
    return merged


def deduplicate(records: Iterable[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], int]:
    unique: dict[str, dict[str, Any]] = {}
    duplicates = 0
    for record in records:
        key = normalize_text(record.get("canonical_id")) or canonical_identity(record)
        if key in unique:
            unique[key] = merge_records(unique[key], record)
            duplicates += 1
        else:
            first = dict(record)
            first["duplicate_count"] = int(first.get("duplicate_count") or 1)
            first["source_ids"] = sorted({normalize_text(first.get("source_id"))} - {""})
            unique[key] = first
    return unique, duplicates


def route_record(record: dict[str, Any], compliance: dict[str, Any]) -> str:
    if not compliance["allowed"]:
        return "quarantined"
    status = normalize_text(record.get("review_status"))
    if status == "approved_for_package":
        return "approved"
    return "manual_review"


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    temporary.replace(path)


def hubspot_token() -> str:
    for name in ("HUBSPOT_ACCESS_TOKEN", "HUBSPOT_SERVICE_KEY", "HUBSPOT_PRIVATE_APP_TOKEN", "HUBSPOT_API_KEY"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def hubspot_properties(record: dict[str, Any]) -> dict[str, str]:
    properties = {
        "company": normalize_text(record.get("name")),
        "phone": normalize_text(record.get("phone")),
        "website": normalize_text(record.get("website")),
        "city": normalize_text(record.get("city")),
        "state": normalize_text(record.get("state")),
        "zip": normalize_text(record.get("postcode")),
        "address": normalize_text(record.get("street")),
    }
    return {key: value for key, value in properties.items() if value}


def export_hubspot(record: dict[str, Any], token: str) -> str:
    payload = json.dumps({"properties": hubspot_properties(record)}).encode("utf-8")
    request = urllib.request.Request(
        "https://api.hubapi.com/crm/v3/objects/contacts",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"HubSpot export failed: {exc}") from exc
    return normalize_text(result.get("id"))


def run_pipeline(records: Iterable[dict[str, Any]], output_dir: Path, *, export_enabled: bool | None = None) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    started_at = utc_now()
    retention_days = positive_int_env("NEXUS_OSINT_RETENTION_DAYS", 365)
    suppression_path = Path(os.environ.get("NEXUS_OSINT_SUPPRESSION_FILE", str(output_dir / "suppression_list.jsonl")))
    suppression_values = load_suppression_values(suppression_path)
    normalized = [normalize_record(record, retention_days) for record in records]
    now = datetime.now(timezone.utc)
    retained = [
        record
        for record in normalized
        if (parse_datetime(normalize_text(record.get("retention_expires_at"))) or now) >= now
    ]
    expired_records = len(normalized) - len(retained)
    unique, duplicate_count = deduplicate(retained)
    approved: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []

    for record in unique.values():
        compliance = compliance_result(record, suppression_values)
        for field in PROHIBITED_FIELDS:
            record.pop(field, None)
        record["compliance"] = compliance
        record["pipeline_route"] = route_record(record, compliance)
        if record["pipeline_route"] == "approved":
            approved.append(record)
        elif record["pipeline_route"] == "quarantined":
            quarantined.append(record)
        else:
            review.append(record)

    export_enabled = truthy_env("NEXUS_OSINT_HUBSPOT_EXPORT") if export_enabled is None else export_enabled
    export_state_path = output_dir / "hubspot_export_state.json"
    export_state: dict[str, Any] = {}
    if export_state_path.exists():
        try:
            loaded = json.loads(export_state_path.read_text(encoding="utf-8"))
            export_state = loaded if isinstance(loaded, dict) else {}
        except (OSError, json.JSONDecodeError):
            export_state = {}
    exported = 0
    export_errors: list[dict[str, str]] = []
    if export_enabled:
        token = hubspot_token()
        if not token:
            export_errors.append({"error": "HubSpot export enabled but no token is configured."})
        else:
            for record in approved:
                lead_id = normalize_text(record.get("lead_id"))
                ledger_key = normalize_text(record.get("canonical_id")) or lead_id
                if not ledger_key or ledger_key in export_state:
                    continue
                try:
                    contact_id = export_hubspot(record, token)
                except RuntimeError as exc:
                    export_errors.append({"lead_id": lead_id, "error": str(exc)})
                    continue
                export_state[ledger_key] = {"lead_id": lead_id, "contact_id": contact_id, "exported_at": utc_now()}
                exported += 1

    ordered = lambda items: sorted(items, key=lambda item: (-int(item.get("score") or 0), normalize_text(item.get("name"))))
    write_jsonl(output_dir / "approved_leads.jsonl", ordered(approved))
    write_jsonl(output_dir / "manual_review_queue.jsonl", ordered(review))
    write_jsonl(output_dir / "compliance_quarantine.jsonl", ordered(quarantined))
    atomic_write_json(export_state_path, export_state)
    finished_at = utc_now()
    summary = {
        "pipeline_version": PIPELINE_VERSION,
        "started_at": started_at,
        "finished_at": finished_at,
        "input_records": len(normalized),
        "expired_records": expired_records,
        "unique_records": len(unique),
        "duplicates_merged": duplicate_count,
        "approved_records": len(approved),
        "manual_review_records": len(review),
        "quarantined_records": len(quarantined),
        "suppression_entries": len(suppression_values),
        "retention_days": retention_days,
        "hubspot_export_enabled": export_enabled,
        "hubspot_exported": exported,
        "hubspot_export_errors": export_errors,
        "outputs": {
            "approved": str(output_dir / "approved_leads.jsonl"),
            "manual_review": str(output_dir / "manual_review_queue.jsonl"),
            "quarantine": str(output_dir / "compliance_quarantine.jsonl"),
            "export_state": str(export_state_path),
        },
    }
    atomic_write_json(output_dir / "pipeline_manifest.json", summary)
    event = {"event": "pipeline_completed", **{key: value for key, value in summary.items() if key not in {"outputs", "hubspot_export_errors"}}}
    with (output_dir / "pipeline_audit.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    active_records = [record for record in unique.values() if record.get("pipeline_route") != "quarantined"]
    return {normalize_text(record.get("lead_id")): record for record in active_records if normalize_text(record.get("lead_id"))}, summary
