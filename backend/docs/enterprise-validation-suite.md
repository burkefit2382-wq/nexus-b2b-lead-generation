# Enterprise Validation Suite

This suite adds repeatable enterprise-grade validation for:

- load/performance
- security controls
- SLA thresholds

It runs against the in-process FastAPI app, so it is deterministic in local and CI environments.

## What it validates

1. **Load and performance**
   - high-volume request runs on `/health` and `/api/health`
   - latency distribution (p50, p95, mean, max)
   - success/failure rates

2. **Security**
   - rejects invalid event names
   - blocks HubSpot export when credentials are missing
   - redacts sensitive config values in status responses
   - avoids exposing HubSpot token material in status output

3. **SLA**
   - per-endpoint success rate threshold
   - p95 latency threshold
   - availability threshold over repeated probes

## Run locally

From repository root:

```powershell
python backend\scripts\enterprise_validation_suite.py
```

## Tunable thresholds

Example with explicit thresholds:

```powershell
python backend\scripts\enterprise_validation_suite.py `
  --requests 400 `
  --concurrency 40 `
  --min-success-rate 99.5 `
  --max-p95-ms 200 `
  --min-availability 99.95
```

## Outputs

- `backend/docs/enterprise-validation-report.md`
- `backend/docs/enterprise-validation-report.json`

The script exits with a non-zero code when any security or SLA check fails, so it can be used as a deployment gate.
