# Incident Response and Rollback Runbook

## Trigger conditions

Use this runbook when:

- `/healthz`, `/health`, or `/api/health` fails
- Stripe checkout or webhooks stop processing
- Resend delivery fails repeatedly
- HubSpot sync starts returning 429/5xx errors
- Cloudflare deploy or routing breaks the public site

## First 15 minutes

1. Confirm blast radius: launch site, tracking API, static assets, or third-party integration only.
2. Check GitHub Actions for the latest `Cloudflare deploy`, `Render backend redeploy`, and `Enterprise Validation` runs.
3. Validate Render health endpoints directly.
4. Verify Cloudflare DNS/proxy/WAF changes from the current release.

## Rollback order

1. Roll back Cloudflare Worker/static bundle if the edge deploy is the issue.
2. Roll back Render services if backend code is the issue.
3. Disable or bypass optional integrations (Resend/HubSpot) only if they are causing noise while core lead capture must stay online.
4. Rotate secrets immediately if compromise is suspected.

## Post-incident

- Capture the failing commit, workflow run IDs, and mitigation timeline.
- Add or tighten tests/runbooks before the next production release.
