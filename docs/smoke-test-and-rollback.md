# Smoke Test Checklist & Rollback Runbook

## Smoke Test Checklist

Run these checks against the Render URL after every deployment before marking it stable.

### Health Endpoints

```bash
BASE_URL=https://nexuscloud.sh   # or staging URL

# 1. Backend health (returns {"status":"ok"})
curl -sf "${BASE_URL}/health" | python3 -m json.tool

# 2. API health (returns {"ok":true,"status":"healthy",...})
curl -sf "${BASE_URL}/api/health" | python3 -m json.tool

# 3. Config-status (confirms DATABASE_URL, JWT, R2, Resend are wired up)
curl -sf "${BASE_URL}/api/config-status" | python3 -m json.tool
```

Expected results:

| Endpoint | Expected key | Expected value |
|---|---|---|
| `/health` | `status` | `"ok"` |
| `/api/health` | `ok` | `true` |
| `/api/config-status` | `databaseUrlConfigured` | `true` |
| `/api/config-status` | `jwtConfigured` | `true` |

### Lead Generation Flow

```bash
# 4. Track a page_view event (requires DATABASE_URL to be set)
curl -sf -X POST "${BASE_URL}/api/event" \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "page_view",
    "client_id": "smoke-test-client",
    "page_url": "https://nexuscloud.sh/"
  }' | python3 -m json.tool

# 5. Track a generate_lead event
curl -sf -X POST "${BASE_URL}/api/event" \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "generate_lead",
    "client_id": "smoke-test-client",
    "page_url": "https://nexuscloud.sh/",
    "utm_source": "smoke_test",
    "event_data": {"form_type": "quote_request", "lead_score": 75}
  }' | python3 -m json.tool

# 6. Mock leads (no DB required)
curl -sf "${BASE_URL}/api/leads/mock?limit=2" | python3 -m json.tool
```

### Neon Database Verification

After running steps 4–5, verify rows appeared in Neon:

```sql
-- Run in Neon SQL editor or local psql
SELECT count(*) FROM visitors;
SELECT count(*) FROM events;
SELECT count(*) FROM leads;
```

Expected: counts increment after each smoke-test run.

### Frontend

- Open `https://nexuscloud.sh` (or the Render static site URL) in a browser.
- Confirm the page loads without console errors.
- Confirm the Lead Control Center UI loads at `/lead-control-center`.

---

## Rollback Runbook

### Option A – Redeploy a previous commit via Render Dashboard

1. Open **Render Dashboard → Service → Deploys**.
2. Locate the last known-good deploy.
3. Click **Redeploy** → confirm.
4. Wait for the deploy to reach **Live**.
5. Re-run the Smoke Test Checklist above.

### Option B – Trigger a rollback deploy via the Render API

```bash
# Replace with actual service ID and deploy ID
RENDER_API_KEY=rnd_xxxxxxxxxxxxxxxxxxxx
RENDER_SERVICE_ID=srv_xxxxxxxxxxxxxxxxxxxx
PREVIOUS_DEPLOY_ID=dep_xxxxxxxxxxxxxxxxxxxx

curl -sf -X POST \
  --header "Authorization: ******" \
  "https://api.render.com/v1/services/${RENDER_SERVICE_ID}/deploys/${PREVIOUS_DEPLOY_ID}/rollback"
```

### Option C – Redeploy a tagged Git release via GitHub Actions

1. Identify the release tag to roll back to (e.g. `v1.0.0-nexus-b2b-prod`):

   ```bash
   git tag --list "v*" --sort=-version:refname | head -5
   ```

2. Push the tag to trigger the `deploy.yml` workflow on that commit:

   ```bash
   git checkout tags/v1.0.0-nexus-b2b-prod -b hotfix/rollback
   git push origin hotfix/rollback
   # Open a PR from hotfix/rollback → main and merge
   ```

3. The `deploy.yml` workflow will fire on the `main` push, run CI, and re-deploy.

### Option D – Database rollback

If a schema migration caused issues, apply the corrective SQL directly in the Neon SQL editor:

```sql
-- Example: drop a column added by mistake
ALTER TABLE leads DROP COLUMN IF EXISTS bad_column;
```

For destructive rollbacks, restore from a Neon branch snapshot:

1. In **Neon Console → Branches**, find the branch created before the bad migration.
2. Click **Restore** → confirm.
3. Update the `DATABASE_URL` secret in GitHub and Render to point at the restored branch connection string.
4. Trigger a fresh deploy so the app picks up the new connection string.

---

## Release Tagging

After a successful deployment and smoke tests, tag the release:

```bash
git tag -a v1.0.0-nexus-b2b-prod -m "Nexus B2B production release v1.0.0"
git push origin v1.0.0-nexus-b2b-prod
```

Then enable branch protection on `main`:

- Require pull requests before merging.
- Require the **CI** status check to pass.
- Do not allow force pushes.
