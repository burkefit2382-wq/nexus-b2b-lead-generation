# Nexus B2B – Deployment Runbook

Operational reference for the Nexus B2B lead generation platform on Render + Neon.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Environments](#environments)
3. [CI/CD Pipeline](#cicd-pipeline)
4. [Rollback Procedure](#rollback-procedure)
5. [Database Migrations](#database-migrations)
6. [Secrets Management](#secrets-management)
7. [Health Checks](#health-checks)
8. [Branch Protection Rules](#branch-protection-rules)
9. [Release Tagging](#release-tagging)
10. [Incident Response](#incident-response)

---

## Architecture Overview

| Layer    | Service                  | Provider |
|----------|--------------------------|----------|
| Frontend | Static site (Vite/TS)    | Render   |
| Backend  | Web service (FastAPI)    | Render   |
| Database | Neon Postgres (pooled)   | Neon     |
| Scraper  | Cron job (Python worker) | Render   |

---

## Environments

| Environment | Branch | Render Service               | Neon Branch   |
|-------------|--------|------------------------------|---------------|
| Production  | `main` | `nexus-b2b-api` (prod)       | primary       |
| Staging     | `dev`  | `nexus-b2b-api` (staging)    | staging       |
| Preview     | PR     | (none – DB branch only)      | `preview/pr-N`|

---

## CI/CD Pipeline

### Trigger flow

```
push / PR  →  ci.yml (lint + test + build)
                  ↓  success
              deploy.yml (Render API deploy)
                  ├── dev branch  → staging service
                  └── main branch → production service
```

### Required GitHub Secrets

| Secret                          | Description                                  |
|---------------------------------|----------------------------------------------|
| `RENDER_API_KEY`                | Render account API key                       |
| `RENDER_STG_SERVICE_ID`         | Staging backend Render service ID            |
| `RENDER_PROD_SERVICE_ID`        | Production backend Render service ID         |
| `RENDER_STG_FRONTEND_SERVICE_ID`  | Staging frontend Render service ID         |
| `RENDER_PROD_FRONTEND_SERVICE_ID` | Production frontend Render service ID      |
| `NEON_API_KEY`                  | Neon API key (preview branch workflow)       |

### Required GitHub Variables (not secrets)

| Variable          | Description               |
|-------------------|---------------------------|
| `NEON_PROJECT_ID` | Neon project ID           |

---

## Rollback Procedure

### Option A – Redeploy a previous commit (< 5 minutes)

1. Find the last known-good commit SHA:
   ```bash
   git log --oneline main | head -10
   ```
2. Create a revert commit:
   ```bash
   git revert <bad-commit-sha> --no-edit
   git push origin main
   ```
   CI will run and `deploy.yml` will automatically redeploy.

### Option B – Trigger a specific Render deploy via API

```bash
curl --request POST \
  --url "https://api.render.com/v1/services/${SERVICE_ID}/deploys" \
  --header "Authorization: ******" \
  --header "Content-Type: application/json" \
  --data '{"commitId": "<known-good-sha>", "clearCache": "do_not_clear"}'
```

### Option C – Roll back via Render Dashboard

1. Render Dashboard → Service → **Deploys** tab
2. Find a previous successful deploy
3. Click **Re-deploy** on that deploy

### Option D – Switch Neon branch (database only)

If only the database is problematic, use Neon's instant restore:

```bash
# Via Neon CLI
neon branches restore <branch-name> --timestamp "2025-01-01T00:00:00Z"
```

---

## Database Migrations

Migrations are applied automatically in the Render build command via `python db/migrate.py`.

### Manual migration

```bash
export DATABASE_URL="postgresql://..."
cd backend
python db/migrate.py
```

### Verify schema

After migration, connect to Neon and check:

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

Expected tables: `events`, `leads`, `migration_history`, `tracking_events`,
`visitors`, `waitlist`, `weekly_summaries`.

### Neon preview branches (PR environments)

The `neon-preview-branches.yml` workflow automatically creates an isolated Neon
branch for each pull request and runs the schema migration on it. The branch is
deleted when the PR closes.

---

## Secrets Management

- **Never commit** `.env`, database connection strings, or API keys.
- All secrets live in **GitHub Secrets** (CI/CD) and **Render Environment Variables** (runtime).
- `DATABASE_URL` must include `sslmode=require&channel_binding=require`.
- Rotate `JWT_SECRET` by updating it in Render and redeploying – no code change needed.
- Rotate `RENDER_API_KEY` by generating a new key in Render → Account Settings → API Keys,
  updating the GitHub Secret, and revoking the old key.

---

## Health Checks

| Service                | Path          | Expected status | Interval |
|------------------------|---------------|-----------------|----------|
| nexus-b2b-api          | `/health`     | 200             | 60 s     |
| nexus-launch-site      | `/healthz`    | 200             | 60 s     |
| nexus-frontend (static)| `/`           | 200             | –        |

Verify manually after each deployment:

```bash
curl -sf https://<backend-url>/health | python3 -m json.tool
curl -sf https://<backend-url>/api/health | python3 -m json.tool
curl -sf https://<backend-url>/api/config-status | python3 -m json.tool
```

---

## Branch Protection Rules

Configure the following rules on GitHub → Settings → Branches for the `main` branch:

- [x] Require a pull request before merging
- [x] Require at least 1 approving review
- [x] Dismiss stale pull request approvals when new commits are pushed
- [x] Require status checks to pass before merging
  - Required checks: `backend`, `frontend` (from `ci.yml`)
- [x] Require branches to be up to date before merging
- [x] Block force pushes
- [x] Restrict who can push to matching branches

---

## Release Tagging

After a production deployment is verified healthy, tag the release:

```bash
git tag -a v1.0.0 -m "Production launch: Nexus B2B v1.0.0"
git push origin v1.0.0
```

Use semantic versioning: `vMAJOR.MINOR.PATCH[-nexus-b2b-<label>]`.

---

## Incident Response

### Deployment failure

1. Check GitHub Actions → **Deploy** workflow run for error details.
2. Check Render Dashboard → Service → **Logs** for build/runtime errors.
3. If the build failed: fix the issue, push to `main` or `dev`; CI will re-trigger deploy.
4. If the service is running but unhealthy: roll back using [Option A or C](#rollback-procedure).

### Database connectivity failure

1. Verify `DATABASE_URL` is set correctly in Render Environment Variables.
2. Check Neon Console → Project → **Monitoring** for active connections and query errors.
3. Confirm SSL flags: `sslmode=require&channel_binding=require`.
4. If the Neon compute is suspended (scale-to-zero), the first connection will resume it automatically.

### Elevated error rate

1. Render Dashboard → Service → **Logs** – filter by `ERROR` or exception tracebacks.
2. Neon Console → **Queries** – look for slow or failing queries.
3. Roll back if errors started after a deployment (see [Rollback Procedure](#rollback-procedure)).
4. Scale up compute in Render or Neon if the issue is resource-related.
