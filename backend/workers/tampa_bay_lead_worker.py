"""Safe Tampa Bay lead collector for Nexus.

Collects public business/location records from OpenStreetMap via Overpass for
Pinellas, Hillsborough, Pasco, and Hernando. It writes buyer-safe business lead
records only: no private identifiers, no bypassing login walls, and no hidden
or personal data collection.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .osint_pipeline import run_pipeline
except ImportError:
    from osint_pipeline import run_pipeline


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "scrapers"
JSONL_PATH = OUT_DIR / "tampa_bay_real_estate_leads.jsonl"
CSV_PATH = OUT_DIR / "tampa_bay_real_estate_leads.csv"
SUMMARY_PATH = OUT_DIR / "latest_summary.json"
STATE_PATH = OUT_DIR / "worker_state.json"
LOG_PATH = OUT_DIR / "worker.log"
METRICS_PATH = OUT_DIR / "worker_metrics.prom"

OVERPASS_URL = os.environ.get("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
USER_AGENT = os.environ.get("NEXUS_SCRAPER_USER_AGENT", "NexusLeadGen/1.0 buyer-safe local lead collector")

COUNTIES = ("Pinellas County", "Hillsborough County", "Pasco County", "Hernando County")

TARGETS = (
    {"kind": "real_estate", "label": "Real estate office", "filters": ('["office"~"estate_agent|real_estate"]', '["shop"="estate_agent"]')},
    {"kind": "mortgage", "label": "Mortgage / finance", "filters": ('["office"~"financial|finance|mortgage"]', '["amenity"="bank"]')},
    {"kind": "insurance", "label": "Insurance office", "filters": ('["office"="insurance"]', '["shop"="insurance"]')},
    {"kind": "home_services", "label": "Home services", "filters": ('["craft"~"roofer|plumber|electrician|hvac"]', '["shop"~"hardware|trade"]')},
    {
        "kind": "professional_cleaning",
        "label": "Home and professional cleaning",
        "filters": (
            '["shop"~"cleaning|laundry|dry_cleaning"]',
            '["craft"~"cleaning|window_cleaning|carpet_cleaning"]',
            '["office"~"cleaning"]',
            '["amenity"~"cleaning"]',
            '["service"~"cleaning|house_cleaning|commercial_cleaning|janitorial"]',
        ),
    },
    {
        "kind": "biopharma",
        "label": "Biopharma / life sciences HQ candidate",
        "filters": (
            '["office"~"research|laboratory|company"]',
            '["healthcare"~"laboratory|pharmacy"]',
            '["amenity"~"research_institute|laboratory|pharmacy"]',
            '["shop"~"pharmacy|medical_supply"]',
            '["name"~"bio|biotech|pharma|therapeutics|life science|clinical|laborator",i]',
        ),
    },
)

FIELDNAMES = (
    "lead_id",
    "name",
    "category",
    "county",
    "city",
    "state",
    "postcode",
    "street",
    "phone",
    "website",
    "source",
    "source_id",
    "latitude",
    "longitude",
    "score",
    "score_notes",
    "osint_quality_score",
    "osint_confidence",
    "osint_flags",
    "osint_sources",
    "quality_band",
    "review_status",
    "collected_at",
)

FLORIDA_BOUNDS = {
    "Pinellas County": {"lat_min": 27.55, "lat_max": 28.22, "lon_min": -82.95, "lon_max": -82.52},
    "Hillsborough County": {"lat_min": 27.50, "lat_max": 28.25, "lon_min": -82.85, "lon_max": -82.05},
    "Pasco County": {"lat_min": 28.15, "lat_max": 28.55, "lon_min": -82.90, "lon_max": -82.00},
    "Hernando County": {"lat_min": 28.40, "lat_max": 28.75, "lon_min": -82.75, "lon_max": -82.00},
}

FLORIDA_STATE_VALUES = {"", "FL", "Florida"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(message: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    line = json.dumps({"ts": utc_now(), "message": message}, sort_keys=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(message, flush=True)


def overpass_query(county: str, target: dict[str, Any]) -> str:
    county_name = county.replace('"', '\\"')
    parts: list[str] = []
    for filter_text in target["filters"]:
        parts.append(f"node{filter_text}(area.searchArea);")
        parts.append(f"way{filter_text}(area.searchArea);")
        parts.append(f"relation{filter_text}(area.searchArea);")
    return "\n".join(
        [
            "[out:json][timeout:60];",
            f'area["name"="{county_name}"]["boundary"="administrative"]["admin_level"="6"]->.searchArea;',
            "(",
            *parts,
            ");",
            "out center tags;",
        ]
    )


def fetch_overpass(query: str, retries: int = 2) -> dict[str, Any]:
    body = urllib.parse.urlencode({"data": query}).encode("utf-8")
    request = urllib.request.Request(
        OVERPASS_URL,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt >= retries:
                raise
            wait_seconds = 45 * (attempt + 1)
            log(f"Overpass rate limit hit; backing off {wait_seconds} seconds")
            time.sleep(wait_seconds)
    raise RuntimeError("Overpass request failed after retries")


def text_value(tags: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = tags.get(key)
        if value:
            return str(value).strip()
    return ""


def normalize_element(element: dict[str, Any], county: str, target: dict[str, Any], collected_at: str) -> dict[str, Any] | None:
    tags = element.get("tags") or {}
    name = text_value(tags, "name", "operator", "brand")
    if not name:
        return None

    lat = element.get("lat") or (element.get("center") or {}).get("lat")
    lon = element.get("lon") or (element.get("center") or {}).get("lon")
    street = " ".join(
        part
        for part in (
            text_value(tags, "addr:housenumber"),
            text_value(tags, "addr:street"),
        )
        if part
    )
    website = text_value(tags, "website", "contact:website", "url")
    phone = text_value(tags, "phone", "contact:phone")
    source_id = f"osm:{element.get('type')}:{element.get('id')}"
    lead_hash = hashlib.sha256(f"{name}|{street}|{county}|{source_id}".lower().encode("utf-8")).hexdigest()[:16]
    osint = osint_quality_check(tags, county, website, phone, street, lat, lon)
    score, notes = score_record(target["kind"], website, phone, street, lat, lon, osint)
    quality_band = quality_band_for(osint["score"])
    review_status = review_status_for(osint["score"], osint["flags"])

    return {
        "lead_id": f"tb-{lead_hash}",
        "name": name,
        "category": target["label"],
        "county": county.replace(" County", ""),
        "city": text_value(tags, "addr:city"),
        "state": text_value(tags, "addr:state") or "FL",
        "postcode": text_value(tags, "addr:postcode"),
        "street": street,
        "phone": phone,
        "website": website,
        "source": "OpenStreetMap Overpass public data",
        "source_id": source_id,
        "latitude": "" if lat is None else str(lat),
        "longitude": "" if lon is None else str(lon),
        "score": score,
        "score_notes": "; ".join(notes),
        "osint_quality_score": osint["score"],
        "osint_confidence": osint["confidence"],
        "osint_flags": "; ".join(osint["flags"]),
        "osint_sources": "; ".join(osint["sources"]),
        "quality_band": quality_band,
        "review_status": review_status,
        "collected_at": collected_at,
    }


def score_record(kind: str, website: str, phone: str, street: str, lat: Any, lon: Any, osint: dict[str, Any]) -> tuple[int, list[str]]:
    score = 55
    notes = ["Public business/location record"]
    if kind == "real_estate":
        score += 22
        notes.append("Direct real estate category")
    elif kind == "biopharma":
        score += 22
        notes.append("Direct biopharma or life sciences public business category")
    elif kind in {"mortgage", "insurance"}:
        score += 15
        notes.append("Adjacent real estate service category")
    else:
        score += 10
        notes.append("Home-service category with real estate buyer relevance")
    if website:
        score += 8
        notes.append("Website available")
    if phone:
        score += 6
        notes.append("Public phone available")
    if street:
        score += 5
        notes.append("Street address available")
    if lat and lon:
        score += 4
        notes.append("Geo coordinates available")
    quality_score = int(osint["score"])
    if quality_score >= 85:
        score += 8
        notes.append("OSINT QA passed with high confidence")
    elif quality_score >= 70:
        score += 3
        notes.append("OSINT QA passed with medium confidence")
    elif quality_score < 55:
        score -= 18
        notes.append("OSINT QA flagged lead for manual review")
    return max(0, min(score, 100)), notes


def osint_quality_check(tags: dict[str, Any], county: str, website: str, phone: str, street: str, lat: Any, lon: Any) -> dict[str, Any]:
    score = 50
    flags: list[str] = []
    sources = ["OpenStreetMap tags"]

    state = text_value(tags, "addr:state")
    city = text_value(tags, "addr:city")
    postcode = text_value(tags, "addr:postcode")
    if state in FLORIDA_STATE_VALUES:
        score += 12
    else:
        score -= 28
        flags.append(f"State mismatch: {state or 'missing'}")

    if coordinates_in_county(county, lat, lon):
        score += 18
        sources.append("County coordinate bounds")
    elif lat is not None and lon is not None:
        score -= 35
        flags.append("Coordinates outside target Florida county bounds")
    else:
        flags.append("Missing coordinates for county QA")

    if website:
        score += 10
        sources.append("Public website")
        if has_business_domain(website):
            score += 5
        else:
            flags.append("Website domain needs manual review")
    else:
        flags.append("Missing website")

    if phone:
        score += 8
        sources.append("Public phone")
    else:
        flags.append("Missing public phone")

    if street and (city or postcode):
        score += 10
        sources.append("Structured address")
    elif street:
        score += 4
        flags.append("Address missing city or postcode")
    else:
        flags.append("Missing street address")

    social_sources = [
        key
        for key in ("contact:facebook", "facebook", "contact:instagram", "instagram", "contact:linkedin", "linkedin")
        if tags.get(key)
    ]
    if social_sources:
        score += min(6, len(social_sources) * 2)
        sources.append("Public social profile tag")

    score = max(0, min(score, 100))
    confidence = "High" if score >= 85 and not flags else "Medium" if score >= 65 else "Low"
    return {"score": score, "confidence": confidence, "flags": flags, "sources": sorted(set(sources))}


def coordinates_in_county(county: str, lat: Any, lon: Any) -> bool:
    if lat is None or lon is None:
        return False
    bounds = FLORIDA_BOUNDS.get(county)
    if not bounds:
        return False
    try:
        lat_value = float(lat)
        lon_value = float(lon)
    except (TypeError, ValueError):
        return False
    return (
        bounds["lat_min"] <= lat_value <= bounds["lat_max"]
        and bounds["lon_min"] <= lon_value <= bounds["lon_max"]
    )


def has_business_domain(website: str) -> bool:
    parsed = urllib.parse.urlparse(website if "://" in website else f"https://{website}")
    host = parsed.netloc.lower()
    if not host:
        return False
    consumer_hosts = ("facebook.com", "instagram.com", "linkedin.com", "x.com", "twitter.com", "yelp.com")
    return not any(host == item or host.endswith(f".{item}") for item in consumer_hosts)


def quality_band_for(score: int) -> str:
    if score >= 85:
        return "High"
    if score >= 65:
        return "Medium"
    return "Low"


def review_status_for(score: int, flags: list[str]) -> str:
    if score >= 85 and not flags:
        return "approved_for_package"
    if score >= 65:
        return "review_recommended"
    return "hold_for_manual_review"


def load_existing() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    if not JSONL_PATH.exists():
        return records
    with JSONL_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            lead_id = str(record.get("lead_id", ""))
            if lead_id:
                apply_osint_quality(record)
                records[lead_id] = record
    return records


def apply_osint_quality(record: dict[str, Any]) -> None:
    county = str(record.get("county") or "").strip()
    county_name = county if county.endswith("County") else f"{county} County"
    category = str(record.get("category") or "").lower()
    kind = (
        "real_estate"
        if "real estate" in category
        else "biopharma"
        if "biopharma" in category or "life sciences" in category
        else "mortgage"
        if "mortgage" in category
        else "insurance"
        if "insurance" in category
        else "home_services"
    )
    tags = {
        "name": record.get("name"),
        "addr:city": record.get("city"),
        "addr:state": record.get("state"),
        "addr:postcode": record.get("postcode"),
    }
    website = str(record.get("website") or "")
    phone = str(record.get("phone") or "")
    street = str(record.get("street") or "")
    lat = record.get("latitude")
    lon = record.get("longitude")
    osint = osint_quality_check(tags, county_name, website, phone, street, lat, lon)
    score, notes = score_record(kind, website, phone, street, lat, lon, osint)
    record["score"] = score
    record["score_notes"] = "; ".join(notes)
    record["osint_quality_score"] = osint["score"]
    record["osint_confidence"] = osint["confidence"]
    record["osint_flags"] = "; ".join(osint["flags"])
    record["osint_sources"] = "; ".join(osint["sources"])
    record["quality_band"] = quality_band_for(osint["score"])
    record["review_status"] = review_status_for(osint["score"], osint["flags"])


def write_outputs(records: dict[str, dict[str, Any]], summary: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ordered = sorted(records.values(), key=lambda item: (-int(item.get("score") or 0), item.get("county", ""), item.get("name", "")))
    with JSONL_PATH.open("w", encoding="utf-8") as handle:
        for record in ordered:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for record in ordered:
            writer.writerow({field: record.get(field, "") for field in FIELDNAMES})
    with SUMMARY_PATH.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
    write_worker_metrics(summary)


def select_counties(raw_counties: str | None) -> tuple[str, ...]:
    if not raw_counties:
        return COUNTIES
    requested = {item.strip().lower().replace(" county", "") for item in raw_counties.split(",") if item.strip()}
    selected = tuple(county for county in COUNTIES if county.lower().replace(" county", "") in requested)
    if not selected:
        raise ValueError(f"No matching counties for: {raw_counties}")
    return selected


def select_targets(raw_targets: str | None) -> tuple[dict[str, Any], ...]:
    if not raw_targets:
        return TARGETS
    requested = {item.strip().lower() for item in raw_targets.split(",") if item.strip()}
    selected = tuple(target for target in TARGETS if target["kind"].lower() in requested)
    if not selected:
        valid = ", ".join(target["kind"] for target in TARGETS)
        raise ValueError(f"No matching targets for: {raw_targets}. Valid targets: {valid}")
    return selected


def run_once(delay_seconds: float = 3.0, counties: tuple[str, ...] = COUNTIES, targets: tuple[dict[str, Any], ...] = TARGETS) -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    collected_at = utc_now()
    records = load_existing()
    before_count = len(records)
    errors: list[dict[str, str]] = []
    source_runs: list[dict[str, Any]] = []

    for county in counties:
        for target in targets:
            query = overpass_query(county, target)
            try:
                payload = fetch_overpass(query)
                elements = payload.get("elements") or []
                added = 0
                for element in elements:
                    record = normalize_element(element, county, target, collected_at)
                    if not record:
                        continue
                    if record["lead_id"] not in records:
                        added += 1
                    records[record["lead_id"]] = record
                source_runs.append({"county": county, "target": target["kind"], "fetched": len(elements), "added": added})
                log(f"{county} / {target['kind']}: fetched {len(elements)}, added {added}")
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
                message = f"{county} / {target['kind']} failed: {exc}"
                errors.append({"county": county, "target": target["kind"], "error": str(exc)})
                log(message)
            time.sleep(delay_seconds)

    new_records = max(len(records) - before_count, 0)
    records, pipeline = run_pipeline(records.values(), OUT_DIR)
    summary = {
        "ok": not errors,
        "source": "OpenStreetMap Overpass public data",
        "counties": [county.replace(" County", "") for county in counties],
        "targets": [target["kind"] for target in targets],
        "total_records": len(records),
        "new_records": new_records,
        "target_records": 1000,
        "coverage_percent": round((len(records) / 1000) * 100, 1),
        "last_run_at": collected_at,
        "source_runs": source_runs,
        "errors": errors,
        "quality": quality_summary(records),
        "pipeline": pipeline,
        "outputs": {
            "jsonl": str(JSONL_PATH),
            "csv": str(CSV_PATH),
            "summary": str(SUMMARY_PATH),
            "log": str(LOG_PATH),
            "metrics": str(METRICS_PATH),
        },
    }
    write_outputs(records, summary)
    with STATE_PATH.open("w", encoding="utf-8") as handle:
        json.dump({"last_run_at": collected_at, "last_summary": summary}, handle, indent=2, sort_keys=True)
    log(f"Run complete: {len(records)} total records, {summary['new_records']} new records")
    return summary


def run_loop(interval_minutes: int, delay_seconds: float, counties: tuple[str, ...], targets: tuple[dict[str, Any], ...]) -> None:
    log(f"Worker loop starting with {interval_minutes} minute interval")
    while True:
        run_once(delay_seconds=delay_seconds, counties=counties, targets=targets)
        log(f"Sleeping {interval_minutes} minutes")
        time.sleep(max(interval_minutes, 1) * 60)


def backfill_quality() -> dict[str, Any]:
    records = load_existing()
    records, pipeline = run_pipeline(records.values(), OUT_DIR)
    summary = {
        "ok": True,
        "source": "OpenStreetMap Overpass public data",
        "mode": "osint_quality_backfill",
        "total_records": len(records),
        "new_records": 0,
        "target_records": 1000,
        "coverage_percent": round((len(records) / 1000) * 100, 1),
        "last_run_at": utc_now(),
        "source_runs": [],
        "errors": [],
        "quality": quality_summary(records),
        "pipeline": pipeline,
        "outputs": {
            "jsonl": str(JSONL_PATH),
            "csv": str(CSV_PATH),
            "summary": str(SUMMARY_PATH),
            "log": str(LOG_PATH),
            "metrics": str(METRICS_PATH),
        },
    }
    write_outputs(records, summary)
    with STATE_PATH.open("w", encoding="utf-8") as handle:
        json.dump({"last_run_at": summary["last_run_at"], "last_summary": summary}, handle, indent=2, sort_keys=True)
    log(f"OSINT quality backfill complete: {len(records)} records")
    return summary


def quality_summary(records: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts = {"approved_for_package": 0, "review_recommended": 0, "hold_for_manual_review": 0}
    for record in records.values():
        status = str(record.get("review_status") or "")
        if status in counts:
            counts[status] += 1
    return counts


def write_worker_metrics(summary: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(worker_metrics_text(summary), encoding="utf-8")


def worker_metrics_text(summary: dict[str, Any]) -> str:
    errors = summary.get("errors", [])
    if not isinstance(errors, list):
        errors = []
    quality = summary.get("quality") if isinstance(summary.get("quality"), dict) else {}
    pipeline = summary.get("pipeline") if isinstance(summary.get("pipeline"), dict) else {}
    last_run = parse_datetime(str(summary.get("last_run_at") or ""))
    last_run_timestamp = int(last_run.timestamp()) if last_run else 0
    ok = 1 if summary.get("ok") is True else 0
    lines = [
        "# HELP nexus_worker_up Whether the Nexus OSINT worker completed its latest execution path.",
        "# TYPE nexus_worker_up gauge",
        f'nexus_worker_up{{worker="tampa_bay_lead_worker"}} {ok}',
        "# HELP nexus_worker_total_records Total public-source OSINT records known to the worker.",
        "# TYPE nexus_worker_total_records gauge",
        f'nexus_worker_total_records{{worker="tampa_bay_lead_worker"}} {int(summary.get("total_records") or 0)}',
        "# HELP nexus_worker_new_records New public-source OSINT records collected in the latest run.",
        "# TYPE nexus_worker_new_records gauge",
        f'nexus_worker_new_records{{worker="tampa_bay_lead_worker"}} {int(summary.get("new_records") or 0)}',
        "# HELP nexus_worker_failed_source_runs Failed source runs in the latest worker execution.",
        "# TYPE nexus_worker_failed_source_runs gauge",
        f'nexus_worker_failed_source_runs{{worker="tampa_bay_lead_worker"}} {len(errors)}',
        "# HELP nexus_worker_last_run_timestamp_seconds Unix timestamp of the latest worker run.",
        "# TYPE nexus_worker_last_run_timestamp_seconds gauge",
        f'nexus_worker_last_run_timestamp_seconds{{worker="tampa_bay_lead_worker"}} {last_run_timestamp}',
        "# HELP nexus_worker_pipeline_duplicates_merged Duplicate business records merged in the latest pipeline run.",
        "# TYPE nexus_worker_pipeline_duplicates_merged gauge",
        f'nexus_worker_pipeline_duplicates_merged{{worker="tampa_bay_lead_worker"}} {int(pipeline.get("duplicates_merged") or 0)}',
        "# HELP nexus_worker_pipeline_quarantined_records Records blocked by compliance controls in the latest pipeline run.",
        "# TYPE nexus_worker_pipeline_quarantined_records gauge",
        f'nexus_worker_pipeline_quarantined_records{{worker="tampa_bay_lead_worker"}} {int(pipeline.get("quarantined_records") or 0)}',
        "# HELP nexus_worker_pipeline_hubspot_export_errors CRM export errors in the latest pipeline run.",
        "# TYPE nexus_worker_pipeline_hubspot_export_errors gauge",
        f'nexus_worker_pipeline_hubspot_export_errors{{worker="tampa_bay_lead_worker"}} {len(pipeline.get("hubspot_export_errors") or [])}',
    ]
    for status in ("approved_for_package", "review_recommended", "hold_for_manual_review"):
        lines.append(f'nexus_worker_quality_records{{worker="tampa_bay_lead_worker",status="{status}"}} {int(quality.get(status) or 0)}')
    return "\n".join(lines) + "\n"


def load_summary() -> dict[str, Any]:
    if not SUMMARY_PATH.exists():
        return {
            "ok": False,
            "total_records": 0,
            "new_records": 0,
            "errors": [{"error": "No worker summary exists yet."}],
            "quality": quality_summary({}),
            "last_run_at": "",
        }
    try:
        data = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "ok": False,
            "total_records": 0,
            "new_records": 0,
            "errors": [{"error": "Worker summary could not be read."}],
            "quality": quality_summary({}),
            "last_run_at": "",
        }
    return data if isinstance(data, dict) else {}


def parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect buyer-safe Tampa Bay real estate lead targets.")
    parser.add_argument("--loop", action="store_true", help="Run forever on an interval.")
    parser.add_argument("--backfill-quality", action="store_true", help="Backfill OSINT QA fields for existing records without scraping.")
    parser.add_argument("--metrics", action="store_true", help="Print Prometheus metrics for the latest worker summary and exit.")
    parser.add_argument("--interval-minutes", type=int, default=int(os.environ.get("NEXUS_SCRAPER_INTERVAL_MINUTES", "360")))
    parser.add_argument("--delay-seconds", type=float, default=float(os.environ.get("NEXUS_SCRAPER_DELAY_SECONDS", "15")))
    parser.add_argument("--counties", default=os.environ.get("NEXUS_SCRAPER_COUNTIES"), help="Comma-separated counties, e.g. Pinellas,Hillsborough,Pasco.")
    parser.add_argument("--targets", default=os.environ.get("NEXUS_SCRAPER_TARGETS"), help="Comma-separated target keys, e.g. professional_cleaning.")
    args = parser.parse_args()
    counties = select_counties(args.counties)
    targets = select_targets(args.targets)

    if args.metrics:
        summary = load_summary()
        print(worker_metrics_text(summary), end="")
        return 0 if summary.get("ok") is True else 1
    if args.backfill_quality:
        summary = backfill_quality()
        print(json.dumps(summary, indent=2, sort_keys=True))
    elif args.loop:
        run_loop(interval_minutes=args.interval_minutes, delay_seconds=args.delay_seconds, counties=counties, targets=targets)
    else:
        summary = run_once(delay_seconds=args.delay_seconds, counties=counties, targets=targets)
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
