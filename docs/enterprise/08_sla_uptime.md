# 08 SLA and Uptime Documentation

## Current Production Health

Verified live endpoints:

| Endpoint | Expected |
| --- | --- |
| `https://nexuscloud.sh/` | 200 |
| `https://nexuscloud.sh/dashboard` | 200 |
| `https://nexuscloud.sh/api/fulfillment-status` | 200 |
| `https://nexuscloud.sh/api/revenue-status` | 200 |
| `https://nexus-b2b-lead-generation.onrender.com/healthz` | 200 |

## Current Hosting Dependencies

| Provider | Role |
| --- | --- |
| Cloudflare | DNS, HTTPS, Tunnel/edge routing |
| Render | Backend web service and worker services |
| Stripe | Checkout and payment webhooks |
| Resend | Email delivery |
| HubSpot | CRM |
| GitHub | Source control and CI/CD |

## SLA Positioning

Until formal monitoring, redundancy, backups, and incident response are complete, position uptime as best-effort production availability rather than a contractual enterprise SLA.

Recommended commercial SLA after hardening:

| Tier | Target |
| --- | --- |
| Public storefront | 99.5% monthly uptime target |
| Paid API/backend | 99.5% monthly uptime target |
| Fulfillment email | Best effort with manual fallback |
| CRM sync | Best effort with retry/manual fallback |

## Health Checks

Recommended automated checks:

```text
GET /healthz
GET /api/health
GET /api/revenue-status
GET /api/fulfillment-status
POST /api/enrich-score with synthetic payload
POST /api/checkout with test-mode catalog item in staging
```

## Alerting

Minimum alerts:

- Public URL returns non-200.
- `/healthz` fails.
- Stripe webhook returns 4xx/5xx.
- Resend delivery fails.
- CRM export fails.
- Worker stops generating fresh lead events.
- Cloudflare Tunnel disconnects.

## Incident Severity

| Severity | Example | Target Response |
| --- | --- | --- |
| SEV-1 | Public site down, checkout broken, webhook failing | 1 hour |
| SEV-2 | Email/CRM delivery degraded | 4 business hours |
| SEV-3 | Dashboard metric stale, noncritical API issue | 1 business day |
| SEV-4 | Documentation/UI issue | Next planned release |

## Backup and Recovery

Current gap:

- Some operational data is stored in local JSONL files.

Recommended:

- Move fulfillment, CRM exports, waitlist, and lead requests to managed database.
- Daily backups.
- Restore drill at least quarterly.
- Export lead/report data to encrypted storage.
- Keep infrastructure-as-code for Cloudflare and Render where possible.

## Failover Plan

Short-term:

1. Confirm Render health.
2. Confirm Cloudflare Tunnel process.
3. Restart Cloudflared or point DNS directly to Render.
4. Use Render URL as emergency fallback.
5. Manually fulfill Stripe orders from dashboard/Stripe if webhook/email is down.

Long-term:

- Use durable custom domain routing to Render or Cloudflare Workers.
- Add database persistence.
- Add queue/retry processing for fulfillment.
- Add uptime monitoring with external alerting.
