# Deployment

## Neon production setup

- Production schema source of truth: `backend/db/schema.sql`
- Use the Neon primary branch for production traffic (for example, `br-...` from Neon Console).
- Use separate Neon branches or roles for staging and production isolation.

Apply migrations manually (Neon SQL editor or local `psql`):

```bash
psql "$DATABASE_URL_PROD" -f backend/db/schema.sql
```

`schema.sql` creates required extensions, tables, and indexes (`visitors`, `leads`, `events`, `weekly_summaries`).

Canonical connection string format:

```text
postgresql://<user>:<password>@<host>.neon.tech/neondb?sslmode=require&channel_binding=require
```

## Render services

Create two Render services connected to this repository:

### Backend API service

```text
Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port 10000
Health Check Path: /health
```

### Frontend static service

```text
Root Directory: frontend
Build Command: npm ci && npm run build
Publish Directory: dist
```

Use the Render region closest to Neon.

## Required environment variables

Set these on each Render service as appropriate:

```text
DATABASE_URL
DATABASE_URL_DEV
DATABASE_URL_STG
DATABASE_URL_PROD
NODE_ENV
API_BASE_URL
JWT_SECRET
REDIS_URL
TRACKING_ALLOWED_ORIGIN
R2_ACCESS_KEY
R2_SECRET_KEY
R2_BUCKET
R2_ENDPOINT_URL
RESEND_API_KEY
```

Backend-specific variables already used by the app:

```text
LAUNCH_HOST=0.0.0.0
PUBLIC_BASE_URL=https://nexuscloud.sh
STRIPE_SECRET_KEY=...
STRIPE_WEBHOOK_SECRET=...
RESEND_FROM=Nexus <sales@nexuscloud.sh>
WAITLIST_NOTIFY_TO=...
LLAMA_CHAT_ENDPOINT=...
LLAMA_CHAT_MODEL=llama3
```

## CI/CD workflows

- `.github/workflows/ci.yml`
  - Runs on push + pull_request to `dev` and `main`
  - Installs dependencies
  - Runs frontend build
  - Runs backend compile check + tests
- `.github/workflows/deploy.yml`
  - Triggers after `CI` succeeds
  - Deploys `dev` to Render staging and `main` to Render production
  - Runs `backend/db/schema.sql` migration before triggering Render deploy API

Required GitHub secrets:

```text
RENDER_API_KEY
RENDER_STG_SERVICE_ID
RENDER_PROD_SERVICE_ID
DATABASE_URL_STG
DATABASE_URL_PROD
```

## Smoke tests (post-deploy)

Run after each deploy:

1. `GET /health`
2. `GET /api/health`
3. `GET /api/config-status`
4. Submit a lead flow in the frontend
5. Confirm Neon receives expected rows in `visitors`, `leads`, and `events`
6. Confirm Render logs show no DB auth/SSL errors

## Rollback runbook

1. Re-deploy the previous healthy commit in Render.
2. If needed, temporarily route traffic to the prior stable branch/tag.
3. Verify smoke checks.
4. Tag stable release (example: `v1.0.0-nexus-b2b-prod`) once recovered.

## Cloudflare Tunnel

For local production-style tunnel testing:

```text
url: http://localhost:4174
```

Start the local service with production variables and `PUBLIC_BASE_URL=https://nexuscloud.sh`.
