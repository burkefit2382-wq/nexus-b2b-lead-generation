from __future__ import annotations

import argparse
import csv
import json
import random
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "name": ("name", "full_name", "contact_name", "firstname", "first_name"),
    "company": ("company", "company_name", "organization", "account"),
    "email": ("email", "work_email", "email_address"),
    "phone": ("phone", "phone_number", "mobile", "mobile_phone"),
    "title": ("title", "job_title", "role", "position"),
    "website": ("website", "domain", "company_website", "url"),
    "linkedin": ("linkedin", "linkedin_url", "linkedin_profile"),
}


@dataclass
class DatasetMetrics:
    source: str
    records: int
    name_present: int
    company_present: int
    email_present: int
    email_valid: int
    phone_present: int
    title_present: int
    website_present: int
    linkedin_present: int
    unique_emails: int
    duplicate_emails: int
    unique_email_domains: int
    quality_score: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark Apollo leads vs Nexus leads.")
    parser.add_argument("--apollo", required=True, help="Path to Apollo CSV or JSON")
    parser.add_argument("--nexus", required=True, help="Path to your leads CSV or JSON")
    parser.add_argument("--sample-size", type=int, default=25, help="Rows sampled from each source")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic sampling")
    parser.add_argument(
        "--output-md",
        default="backend/docs/lead-benchmark-report.md",
        help="Markdown report output path (relative to repo root)",
    )
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Input not found: {path}")

    if path.suffix.lower() == ".json":
        return read_json_rows(path)
    return read_csv_rows(path)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no headers: {path}")

        normalized_fields = [normalize_header(field) for field in reader.fieldnames]
        rows: list[dict[str, str]] = []
        for raw_row in reader:
            row: dict[str, str] = {}
            for idx, key in enumerate(reader.fieldnames):
                norm_key = normalized_fields[idx]
                value = raw_row.get(key, "")
                row[norm_key] = "" if value is None else str(value).strip()
            rows.append(row)
        return rows


def read_json_rows(path: Path) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict):
        raw_rows = payload.get("leads", [])
    elif isinstance(payload, list):
        raw_rows = payload
    else:
        raise ValueError(f"Unsupported JSON structure in {path}")

    if not isinstance(raw_rows, list):
        raise ValueError(f"Expected a list of leads in {path}")

    rows: list[dict[str, str]] = []
    for item in raw_rows:
        if not isinstance(item, dict):
            continue
        row = {normalize_header(str(key)): "" if value is None else str(value).strip() for key, value in item.items()}
        rows.append(row)
    return rows


def normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def sample_rows(rows: list[dict[str, str]], sample_size: int, seed: int) -> list[dict[str, str]]:
    if sample_size <= 0:
        raise ValueError("sample-size must be greater than zero")
    if len(rows) <= sample_size:
        return list(rows)
    rng = random.Random(seed)
    return rng.sample(rows, sample_size)


def find_value(row: dict[str, str], field: str) -> str:
    if field == "name":
        first_name = row.get("first_name", "").strip()
        last_name = row.get("last_name", "").strip()
        combined = " ".join(part for part in (first_name, last_name) if part)
        if combined:
            return combined

    aliases = FIELD_ALIASES[field]
    for alias in aliases:
        if alias in row and row[alias].strip():
            return row[alias].strip()

    # fallback for partial matches like "business_email" or "linkedin_profile_url"
    for key, value in row.items():
        if not value:
            continue
        if any(alias in key for alias in aliases):
            return value.strip()
    return ""


def is_valid_email(value: str) -> bool:
    return bool(value and EMAIL_RE.match(value.strip().lower()))


def is_present(value: str) -> bool:
    return bool(value and value.strip())


def email_domain(value: str) -> str:
    email = value.strip().lower()
    if "@" not in email:
        return ""
    return email.split("@", 1)[1]


def to_pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def compute_metrics(source: str, rows: list[dict[str, str]]) -> DatasetMetrics:
    emails: list[str] = []
    name_present = company_present = email_present = email_valid = 0
    phone_present = title_present = website_present = linkedin_present = 0

    for row in rows:
        name = find_value(row, "name")
        company = find_value(row, "company")
        email = find_value(row, "email").lower()
        phone = find_value(row, "phone")
        title = find_value(row, "title")
        website = find_value(row, "website")
        linkedin = find_value(row, "linkedin")

        name_present += int(is_present(name))
        company_present += int(is_present(company))
        email_present += int(is_present(email))
        email_valid += int(is_valid_email(email))
        phone_present += int(is_present(phone))
        title_present += int(is_present(title))
        website_present += int(is_present(website))
        linkedin_present += int(is_present(linkedin))

        if is_present(email):
            emails.append(email)

    unique_emails = len(set(emails))
    duplicate_emails = len(emails) - unique_emails
    unique_domains = len({email_domain(email) for email in emails if email_domain(email)})

    records = len(rows)
    # weighted quality score (0-100)
    quality_score = round(
        (to_pct(name_present, records) * 0.1)
        + (to_pct(company_present, records) * 0.2)
        + (to_pct(email_valid, records) * 0.35)
        + (to_pct(phone_present, records) * 0.1)
        + (to_pct(title_present, records) * 0.1)
        + (to_pct(website_present, records) * 0.1)
        + (to_pct(linkedin_present, records) * 0.05),
        2,
    )

    return DatasetMetrics(
        source=source,
        records=records,
        name_present=name_present,
        company_present=company_present,
        email_present=email_present,
        email_valid=email_valid,
        phone_present=phone_present,
        title_present=title_present,
        website_present=website_present,
        linkedin_present=linkedin_present,
        unique_emails=unique_emails,
        duplicate_emails=duplicate_emails,
        unique_email_domains=unique_domains,
        quality_score=quality_score,
    )


def email_overlap(rows_a: list[dict[str, str]], rows_b: list[dict[str, str]]) -> int:
    emails_a = {find_value(row, "email").strip().lower() for row in rows_a if is_valid_email(find_value(row, "email"))}
    emails_b = {find_value(row, "email").strip().lower() for row in rows_b if is_valid_email(find_value(row, "email"))}
    return len(emails_a.intersection(emails_b))


def domain_overlap(rows_a: list[dict[str, str]], rows_b: list[dict[str, str]]) -> int:
    domains_a = {
        email_domain(find_value(row, "email"))
        for row in rows_a
        if email_domain(find_value(row, "email"))
    }
    domains_b = {
        email_domain(find_value(row, "email"))
        for row in rows_b
        if email_domain(find_value(row, "email"))
    }
    return len(domains_a.intersection(domains_b))


def metrics_table_row(metrics: DatasetMetrics) -> str:
    return (
        f"| {metrics.source} | {metrics.records} | "
        f"{to_pct(metrics.name_present, metrics.records):.2f}% | "
        f"{to_pct(metrics.company_present, metrics.records):.2f}% | "
        f"{to_pct(metrics.email_valid, metrics.records):.2f}% | "
        f"{to_pct(metrics.phone_present, metrics.records):.2f}% | "
        f"{to_pct(metrics.title_present, metrics.records):.2f}% | "
        f"{to_pct(metrics.website_present, metrics.records):.2f}% | "
        f"{to_pct(metrics.linkedin_present, metrics.records):.2f}% | "
        f"{metrics.unique_emails} | {metrics.duplicate_emails} | {metrics.unique_email_domains} | "
        f"{metrics.quality_score:.2f} |"
    )


def write_report(
    output_path: Path,
    apollo_metrics: DatasetMetrics,
    nexus_metrics: DatasetMetrics,
    apollo_rows: list[dict[str, str]],
    nexus_rows: list[dict[str, str]],
) -> None:
    overlap_emails = email_overlap(apollo_rows, nexus_rows)
    overlap_domains = domain_overlap(apollo_rows, nexus_rows)

    winner = "Tie"
    if apollo_metrics.quality_score > nexus_metrics.quality_score:
        winner = "Apollo"
    elif nexus_metrics.quality_score > apollo_metrics.quality_score:
        winner = "Nexus"

    generated_at = datetime.now(timezone.utc).isoformat()

    content = "\n".join(
        [
            "# Lead Benchmark Report: Apollo vs Nexus",
            "",
            f"Generated at (UTC): `{generated_at}`",
            "",
            "## Scope",
            "",
            f"- Apollo sampled leads: **{apollo_metrics.records}**",
            f"- Nexus sampled leads: **{nexus_metrics.records}**",
            "",
            "## Data quality benchmark",
            "",
            "| Source | Records | Name % | Company % | Valid Email % | Phone % | Title % | Website % | LinkedIn % | Unique Emails | Duplicate Emails | Unique Email Domains | Quality Score |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            metrics_table_row(apollo_metrics),
            metrics_table_row(nexus_metrics),
            "",
            "## Cross-dataset overlap",
            "",
            f"- Exact email overlap count: **{overlap_emails}**",
            f"- Email domain overlap count: **{overlap_domains}**",
            "",
            "## Outcome",
            "",
            f"- Higher benchmark quality score: **{winner}**",
            "- Use this as a directional quality benchmark; adjust weights in script if your priorities differ.",
            "",
            "## Notes",
            "",
            "- Valid email check uses basic format validation only.",
            "- Metrics are computed on sampled rows, not your entire source files.",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]

    apollo_path = Path(args.apollo)
    nexus_path = Path(args.nexus)
    if not apollo_path.is_absolute():
        apollo_path = repo_root / apollo_path
    if not nexus_path.is_absolute():
        nexus_path = repo_root / nexus_path

    output_md = Path(args.output_md)
    if not output_md.is_absolute():
        output_md = repo_root / output_md

    apollo_rows = read_rows(apollo_path)
    nexus_rows = read_rows(nexus_path)

    sampled_apollo = sample_rows(apollo_rows, args.sample_size, args.seed)
    sampled_nexus = sample_rows(nexus_rows, args.sample_size, args.seed)

    apollo_metrics = compute_metrics("Apollo", sampled_apollo)
    nexus_metrics = compute_metrics("Nexus", sampled_nexus)

    write_report(output_md, apollo_metrics, nexus_metrics, sampled_apollo, sampled_nexus)

    print(f"Report written: {output_md}")
    print(f"Apollo quality score: {apollo_metrics.quality_score:.2f}")
    print(f"Nexus quality score: {nexus_metrics.quality_score:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
