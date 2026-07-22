from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

import httpx

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
for candidate in (str(REPO_ROOT), str(BACKEND_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

try:
    from backend.app.main import app
except ModuleNotFoundError:
    from app.main import app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run enterprise validation checks (load, security, SLA).")
    parser.add_argument("--requests", type=int, default=250, help="Requests per endpoint for load profiling.")
    parser.add_argument("--concurrency", type=int, default=25, help="Concurrent request workers.")
    parser.add_argument("--availability-probes", type=int, default=40, help="Probe count for SLA availability checks.")
    parser.add_argument("--availability-interval-ms", type=int, default=150, help="Delay between availability probes.")
    parser.add_argument("--min-success-rate", type=float, default=99.0, help="Minimum per-endpoint success rate.")
    parser.add_argument("--max-p95-ms", type=float, default=250.0, help="Maximum per-endpoint p95 latency (ms).")
    parser.add_argument("--min-availability", type=float, default=99.9, help="Minimum service availability percentage.")
    parser.add_argument(
        "--output-md",
        default="backend/docs/enterprise-validation-report.md",
        help="Markdown report output path (relative to repo root).",
    )
    parser.add_argument(
        "--output-json",
        default="backend/docs/enterprise-validation-report.json",
        help="JSON report output path (relative to repo root).",
    )
    return parser.parse_args()


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (pct / 100.0) * (len(ordered) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = rank - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


@contextmanager
def temp_env(overrides: dict[str, str | None]):
    prior = {key: os.environ.get(key) for key in overrides}
    try:
        for key, value in overrides.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in prior.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


async def run_load_profile(
    client: httpx.AsyncClient,
    endpoint: str,
    total_requests: int,
    concurrency: int,
) -> dict[str, Any]:
    semaphore = asyncio.Semaphore(concurrency)
    latencies: list[float] = []
    success = 0
    failures: list[str] = []

    async def one_request() -> None:
        nonlocal success
        start = time.perf_counter()
        try:
            async with semaphore:
                response = await client.get(endpoint)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            latencies.append(elapsed_ms)
            if 200 <= response.status_code < 300:
                success += 1
            else:
                failures.append(f"{response.status_code}")
        except Exception as exc:  # noqa: BLE001 - report concrete error in output.
            failures.append(str(exc))
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            latencies.append(elapsed_ms)

    await asyncio.gather(*(one_request() for _ in range(total_requests)))
    total = len(latencies)
    success_rate = (success / total) * 100.0 if total else 0.0
    return {
        "endpoint": endpoint,
        "total": total,
        "success": success,
        "failure": total - success,
        "success_rate": round(success_rate, 2),
        "p50_ms": round(percentile(latencies, 50), 2),
        "p95_ms": round(percentile(latencies, 95), 2),
        "max_ms": round(max(latencies) if latencies else 0.0, 2),
        "mean_ms": round(mean(latencies) if latencies else 0.0, 2),
        "sample_failures": failures[:5],
    }


async def run_availability_check(
    client: httpx.AsyncClient,
    endpoint: str,
    probes: int,
    interval_ms: int,
) -> dict[str, Any]:
    successes = 0
    latencies: list[float] = []
    for _ in range(probes):
        start = time.perf_counter()
        try:
            response = await client.get(endpoint)
            latencies.append((time.perf_counter() - start) * 1000.0)
            if 200 <= response.status_code < 300:
                successes += 1
        except Exception:
            latencies.append((time.perf_counter() - start) * 1000.0)
        await asyncio.sleep(interval_ms / 1000.0)

    availability = (successes / probes) * 100.0 if probes else 0.0
    return {
        "endpoint": endpoint,
        "probes": probes,
        "successes": successes,
        "availability_pct": round(availability, 2),
        "p95_ms": round(percentile(latencies, 95), 2),
    }


async def run_security_checks(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    response = await client.post("/api/event", json={"event_name": "invalid_event_name"})
    checks.append(
        {
            "name": "Reject unknown event names",
            "passed": response.status_code == 400,
            "details": f"status={response.status_code}",
        }
    )

    with temp_env({"HUBSPOT_ACCESS_TOKEN": None, "HUBSPOT_SERVICE_KEY": None, "HUBSPOT_PRIVATE_APP_TOKEN": None, "HUBSPOT_API_KEY": None}):
        response = await client.post("/api/hubspot-export", json={"lead": {"email": "security-test@example.com", "name": "Security Test"}})
        body = response.json()
        checks.append(
            {
                "name": "Block HubSpot export without credentials",
                "passed": response.status_code == 503 and body.get("ok") is False,
                "details": f"status={response.status_code}",
            }
        )

    redaction_secret = "never-print-this-secret"
    with temp_env(
        {
            "DATABASE_URL": "postgresql://user:pass@example.com/db",
            "JWT_SECRET": redaction_secret,
            "HUBSPOT_ACCESS_TOKEN": "pat-do-not-leak-token",
        }
    ):
        response = await client.get("/api/config-status")
        body = response.text
        leaked = any(token in body for token in (redaction_secret, "example.com", "pat-do-not-leak-token"))
        checks.append(
            {
                "name": "Redact secret config values",
                "passed": response.status_code == 200 and not leaked,
                "details": f"status={response.status_code}",
            }
        )

        hubspot_status = await client.get("/api/hubspot-status")
        leaked_hubspot_token = "pat-do-not-leak-token" in hubspot_status.text
        checks.append(
            {
                "name": "Do not expose HubSpot token in status response",
                "passed": hubspot_status.status_code == 200 and not leaked_hubspot_token,
                "details": f"status={hubspot_status.status_code}",
            }
        )

    return checks


def evaluate_sla(
    load_results: list[dict[str, Any]],
    availability_result: dict[str, Any],
    min_success_rate: float,
    max_p95_ms: float,
    min_availability: float,
) -> list[dict[str, Any]]:
    sla_checks: list[dict[str, Any]] = []

    for result in load_results:
        sla_checks.append(
            {
                "name": f"{result['endpoint']} success rate >= {min_success_rate:.2f}%",
                "passed": result["success_rate"] >= min_success_rate,
                "details": f"actual={result['success_rate']:.2f}%",
            }
        )
        sla_checks.append(
            {
                "name": f"{result['endpoint']} p95 <= {max_p95_ms:.2f}ms",
                "passed": result["p95_ms"] <= max_p95_ms,
                "details": f"actual={result['p95_ms']:.2f}ms",
            }
        )

    sla_checks.append(
        {
            "name": f"Availability >= {min_availability:.2f}%",
            "passed": availability_result["availability_pct"] >= min_availability,
            "details": f"actual={availability_result['availability_pct']:.2f}%",
        }
    )
    return sla_checks


def render_markdown_report(
    generated_at: str,
    load_results: list[dict[str, Any]],
    security_checks: list[dict[str, Any]],
    sla_checks: list[dict[str, Any]],
    availability_result: dict[str, Any],
) -> str:
    overall_passed = all(item["passed"] for item in [*security_checks, *sla_checks])
    outcome = "PASS" if overall_passed else "FAIL"

    lines = [
        "# Enterprise Validation Report",
        "",
        f"Generated at (UTC): `{generated_at}`",
        "",
        "## Outcome",
        "",
        f"- Suite result: **{outcome}**",
        "- Coverage: **Load/Performance**, **Security**, and **SLA** checks.",
        "",
        "## Load and performance",
        "",
        "| Endpoint | Total | Success | Failure | Success % | P50 (ms) | P95 (ms) | Mean (ms) | Max (ms) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in load_results:
        lines.append(
            f"| {result['endpoint']} | {result['total']} | {result['success']} | {result['failure']} | "
            f"{result['success_rate']:.2f}% | {result['p50_ms']:.2f} | {result['p95_ms']:.2f} | "
            f"{result['mean_ms']:.2f} | {result['max_ms']:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Security checks",
            "",
            "| Check | Result | Details |",
            "|---|---|---|",
        ]
    )
    for check in security_checks:
        lines.append(f"| {check['name']} | {'PASS' if check['passed'] else 'FAIL'} | {check['details']} |")

    lines.extend(
        [
            "",
            "## SLA checks",
            "",
            f"- Availability probes: **{availability_result['probes']}** on `{availability_result['endpoint']}`",
            f"- Measured availability: **{availability_result['availability_pct']:.2f}%**",
            f"- Availability p95 latency: **{availability_result['p95_ms']:.2f} ms**",
            "",
            "| Check | Result | Details |",
            "|---|---|---|",
        ]
    )
    for check in sla_checks:
        lines.append(f"| {check['name']} | {'PASS' if check['passed'] else 'FAIL'} | {check['details']} |")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- This suite executes against the in-process FastAPI app to provide deterministic validation in CI.",
            "- Thresholds are configurable by CLI flags for stricter production gates.",
        ]
    )

    return "\n".join(lines) + "\n"


async def run_suite(args: argparse.Namespace) -> dict[str, Any]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=10.0) as client:
        load_results = await asyncio.gather(
            run_load_profile(client, "/health", args.requests, args.concurrency),
            run_load_profile(client, "/api/health", args.requests, args.concurrency),
        )
        availability_result = await run_availability_check(
            client,
            "/health",
            probes=args.availability_probes,
            interval_ms=args.availability_interval_ms,
        )
        security_checks = await run_security_checks(client)

    sla_checks = evaluate_sla(
        load_results,
        availability_result,
        min_success_rate=args.min_success_rate,
        max_p95_ms=args.max_p95_ms,
        min_availability=args.min_availability,
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "load_results": load_results,
        "availability": availability_result,
        "security_checks": security_checks,
        "sla_checks": sla_checks,
    }


def main() -> int:
    args = parse_args()
    repo_root = REPO_ROOT
    output_md = Path(args.output_md)
    output_json = Path(args.output_json)
    if not output_md.is_absolute():
        output_md = repo_root / output_md
    if not output_json.is_absolute():
        output_json = repo_root / output_json

    results = asyncio.run(run_suite(args))
    markdown = render_markdown_report(
        generated_at=results["generated_at"],
        load_results=results["load_results"],
        security_checks=results["security_checks"],
        sla_checks=results["sla_checks"],
        availability_result=results["availability"],
    )

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(markdown, encoding="utf-8")
    output_json.write_text(json.dumps(results, indent=2), encoding="utf-8")

    all_checks = [*results["security_checks"], *results["sla_checks"]]
    failed = [check for check in all_checks if not check["passed"]]
    print(f"Enterprise validation markdown report: {output_md}")
    print(f"Enterprise validation JSON report: {output_json}")
    if failed:
        print("Suite result: FAIL")
        for check in failed:
            print(f" - {check['name']} ({check['details']})")
        return 1

    print("Suite result: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
