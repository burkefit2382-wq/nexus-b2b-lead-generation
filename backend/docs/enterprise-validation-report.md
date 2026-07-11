# Enterprise Validation Report

Generated at (UTC): `2026-07-11T23:13:07.288809+00:00`

## Outcome

- Suite result: **PASS**
- Coverage: **Load/Performance**, **Security**, and **SLA** checks.

## Load and performance

| Endpoint | Total | Success | Failure | Success % | P50 (ms) | P95 (ms) | Mean (ms) | Max (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| /health | 250 | 250 | 0 | 100.00% | 248.43 | 406.08 | 235.78 | 422.31 |
| /api/health | 250 | 250 | 0 | 100.00% | 246.76 | 411.68 | 240.53 | 414.55 |

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
- Availability p95 latency: **1.77 ms**

| Check | Result | Details |
|---|---|---|
| /health success rate >= 99.00% | PASS | actual=100.00% |
| /health p95 <= 500.00ms | PASS | actual=406.08ms |
| /api/health success rate >= 99.00% | PASS | actual=100.00% |
| /api/health p95 <= 500.00ms | PASS | actual=411.68ms |
| Availability >= 99.90% | PASS | actual=100.00% |
