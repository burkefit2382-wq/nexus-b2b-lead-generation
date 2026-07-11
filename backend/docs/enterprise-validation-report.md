# Enterprise Validation Report

Generated at (UTC): `2026-07-11T23:10:48.401053+00:00`

## Outcome

- Suite result: **PASS**
- Coverage: **Load/Performance**, **Security**, and **SLA** checks.

## Load and performance

| Endpoint | Total | Success | Failure | Success % | P50 (ms) | P95 (ms) | Mean (ms) | Max (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| /health | 250 | 250 | 0 | 100.00% | 241.78 | 415.52 | 238.17 | 421.51 |
| /api/health | 250 | 250 | 0 | 100.00% | 241.45 | 410.47 | 237.04 | 414.50 |

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
- Availability p95 latency: **1.73 ms**

| Check | Result | Details |
|---|---|---|
| /health success rate >= 99.00% | PASS | actual=100.00% |
| /health p95 <= 500.00ms | PASS | actual=415.52ms |
| /api/health success rate >= 99.00% | PASS | actual=100.00% |
| /api/health p95 <= 500.00ms | PASS | actual=410.47ms |
| Availability >= 99.90% | PASS | actual=100.00% |
