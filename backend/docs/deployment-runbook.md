# Deployment Runbook

## Supported path

The primary supported deployment path is:

1. **Render** for backend services
2. **Cloudflare** in front of Render for DNS/CDN/WAF/Workers/static assets

Azure, Railway, and Vercel files remain in the repository for legacy/testing purposes, but they are not the primary enterprise deployment path.

## Environments

- **Development** -> `develop` branch -> `Development` GitHub environment -> Render dev deploy hooks
- **Staging** -> `staging` branch -> `Staging` GitHub environment -> Render staging deploy hooks
- **Production** -> `main` branch -> `Production` GitHub environment -> Render prod deploy hooks

## Render setup

### Services

- `nexus-launch-site` (web, Python, **standard** in production)
- `nexus-tracking-api` (web, Python, **standard** in production)
- `nexus-osint-scraper-quality` (cron, starter or higher depending worker SLA)

### Health checks

- Launch site: `/healthz`
- Tracking API: `/health`

### Required production secrets

- `DATABASE_URL`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_API_VERSION`
- `PRICE_ID`
- `RESEND_API_KEY`
- `RESEND_FROM`
- `EMAIL_DOMAIN`
- `WAITLIST_NOTIFY_TO`
- `HUBSPOT_PRIVATE_APP_TOKEN` (canonical)
- `HUBSPOT_PORTAL_ID`

Legacy HubSpot env var names remain accepted for backward compatibility:
`HUBSPOT_ACCESS_TOKEN`, `HUBSPOT_SERVICE_KEY`, `HUBSPOT_API_KEY`.

## GitHub Actions setup

### Render redeploy workflow

Configure these repository or environment secrets:

- `RENDER_DEV_LAUNCH_SITE_DEPLOY_HOOK`
- `RENDER_DEV_TRACKING_API_DEPLOY_HOOK`
- `RENDER_STAGING_LAUNCH_SITE_DEPLOY_HOOK`
- `RENDER_STAGING_TRACKING_API_DEPLOY_HOOK`
- `RENDER_PROD_LAUNCH_SITE_DEPLOY_HOOK`
- `RENDER_PROD_TRACKING_API_DEPLOY_HOOK`

The workflow now fails clearly if any required hook secret is missing.

### Environment protection

GitHub environment protections are configured in the GitHub UI, not in workflow YAML. For enterprise readiness:

- Require reviewers for `Production`
- Restrict who can deploy to `Production`
- Store production-only deploy hooks/secrets in the `Production` environment

## Cloudflare deployment

1. Configure `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`.
2. Run `.github/workflows/cloudflare-deploy.yml` manually or on `main`.
3. The workflow validates secrets, runs backend tests, builds the frontend bundle, and then runs `npm run cf:deploy`.

## Rollback

### Render

- Redeploy the last known-good commit via Render dashboard or re-run the Render deploy hook from the previous release commit.
- Verify `/healthz`, `/health`, `/api/health`, and payment/email smoke tests after rollback.

### Cloudflare

- Re-deploy the previous Worker bundle/version.
- Revert any cache rule, WAF, or DNS change that shipped with the failed release.
- Purge affected cache entries if stale responses are being served.
