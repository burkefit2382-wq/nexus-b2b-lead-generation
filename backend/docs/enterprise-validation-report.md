# Enterprise Validation Report

Generated at (UTC): `2026-07-09T18:57:03.820494+00:00`

## Outcome

- Suite result: **PASS**
- Coverage: **Load/Performance**, **Security**, and **SLA** checks.

## Load and performance

| Endpoint | Total | Success | Failure | Success % | P50 (ms) | P95 (ms) | Mean (ms) | Max (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| /health | 250 | 250 | 0 | 100.00% | 56.75 | 101.11 | 63.34 | 130.25 |
| /api/health | 250 | 250 | 0 | 100.00% | 59.59 | 108.63 | 63.27 | 115.21 |

## Security checks

| Check | Result | Details |
|---|---|---|
| Reject unknown event names | PASS | status=400 |
| Block HubSpot export without credentials | PASS | status=503 |
| Redact secret config values | PASS | status=200 |
| Do not expose HubSpot token in status response | PASS | status=200 |

## SLA checks

- Availability probes: **40** on `/health`
- Measured availability: **100.00%**
- Availability p95 latency: **5.88 ms**

| Check | Result | Details |
|---|---|---|
| /health success rate >= 99.00% | PASS | actual=100.00% |
| /health p95 <= 250.00ms | PASS | actual=101.11ms |
| /api/health success rate >= 99.00% | PASS | actual=100.00% |
| /api/health p95 <= 250.00ms | PASS | actual=108.63ms |
| Availability >= 99.90% | PASS | actual=100.00% |

## Notes

- This suite executes against the in-process FastAPI app to provide deterministic validation in CI.
- Thresholds are configurable by CLI flags for stricter production gates.
