# GOV Readiness Health and Metrics Baseline

This document freezes the first GOV-readiness endpoint contract for NEXUS services.

## Mandatory Endpoints

HTTP services expose:

- `/health`: liveness status for process supervision.
- `/ready`: readiness status for Kubernetes routing and production configuration gates.
- `/metrics`: Prometheus text metrics for uptime, readiness, scraper totals, worker failures, and quality distribution.

The legacy `/healthz` endpoint remains available as a compatibility alias for existing uptime checks.

## Covered Services

- FastAPI backend: `/health`, `/ready`, `/metrics`, `/api/health`, `/healthz`.
- Launch fallback server: `/health`, `/ready`, `/metrics`, `/api/health`, `/healthz`.
- OSINT worker and CronJobs: Prometheus worker metrics are written to `worker_metrics.prom`, and `--metrics` prints the latest worker metrics for Kubernetes exec probes and operational evidence.

Parser service and model server endpoints must follow the same contract when those services are added as separately deployed components.

## Kubernetes Baseline

- `nexus-api` liveness probe uses `/health`.
- `nexus-api` readiness probe uses `/ready`.
- `nexus-api` pod annotations advertise `/metrics` for Prometheus scraping.
- `nexus-worker` liveness and readiness probes execute the worker `--metrics` path.
- `nexus-internal-health` validates `/health`, `/ready`, `/metrics`, and `/api/health` inside the cluster.

## Production Readiness Rule

In non-production environments, `/ready` confirms that the app can serve and its local data paths are usable.

In `ENVIRONMENT=production`, `/ready` also requires production configuration to be present without exposing secret values. Required checks include database, JWT, Stripe, Resend, and HubSpot configuration for the FastAPI service.

## Compliance Use

This endpoint baseline supports:

- Kubernetes autoscaling and rollout gates.
- Prometheus/Grafana dashboards.
- Uptime and synthetic checks.
- SLA/SLO evidence.
- GOV-readiness review artifacts for NIST 800-53 and FedRAMP Moderate preparation.
