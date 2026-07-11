# Architecture Overview

## Canonical production path

```text
Browser
  -> Cloudflare DNS/CDN/WAF/Workers/static assets
  -> Render standard web service: nexus-launch-site
  -> Render standard web service: nexus-tracking-api
  -> Neon Postgres

Render services also integrate with:
- Resend for transactional email
- Stripe for checkout + signed webhooks
- HubSpot for CRM sync
```

## Responsibilities

- **Cloudflare**: DNS, TLS termination, CDN caching for static assets, WAF, edge retries for static asset fetches, and deployment of the Worker/asset bundle.
- **Render launch site** (`backend/server.py`): storefront, command dashboard, Stripe checkout creation, Stripe webhook fulfillment, Resend delivery, HubSpot demo export, and launch-site health reporting.
- **Render tracking API** (`backend/app/main.py`): FastAPI lead CRUD, membership API, event ingestion, health/config visibility, and Neon-backed data access.
- **Neon Postgres**: system-of-record database for lead and membership state.
- **Resend / Stripe / HubSpot**: external SaaS dependencies that must be configured in production but degrade gracefully when optional flows are unavailable.

## Availability model

- Production Render web services should run on **Standard** or higher to avoid free-tier sleep/cold-start behavior.
- Cloudflare remains in **proxied** mode in front of Render so DNS, WAF, and caching policies stay centralized.
- `/healthz` and `/health` now report dependency state; required dependencies fail readiness loudly while optional integrations report `degraded` without taking the whole service down.

## Edge and security controls

- Cloudflare WAF/rate limiting should protect public routes before traffic reaches Render.
- Static responses should include HSTS, CSP, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and `Permissions-Policy`.
- Stripe webhook requests must be signature verified before any fulfillment logic runs.
- Secrets stay in Render environment groups, GitHub Actions secrets/environments, and Cloudflare secrets only.
