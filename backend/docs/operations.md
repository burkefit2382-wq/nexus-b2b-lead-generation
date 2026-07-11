# Operations Runbook

## Launch Checklist

- Confirm `/healthz` and `/health` return `healthy` or `degraded` with the expected dependency details.
- Confirm `PUBLIC_BASE_URL` is set to the public domain.
- Confirm Stripe Checkout returns a hosted URL for each visible buy button.
- Confirm retired/cheap catalog IDs return `400`.
- Confirm `STRIPE_WEBHOOK_SECRET` is set and the webhook endpoint is active.
- Confirm Resend domain is verified and `RESEND_FROM` uses that domain.
- Confirm fulfillment events appear after test checkout.
- Confirm dashboard loads without broken components.

## Scraper Operations

Use safe, moderate pacing for public data sources. Avoid bypassing protections, rate limits, login walls, or platform terms.

Track:

- Source
- County or territory
- Start time
- Delay between requests
- Error count
- Records accepted
- Records rejected
- Last successful run

## Incident Response

1. Pause affected workflow.
2. Preserve logs.
3. Rotate exposed credentials.
4. Disable impacted checkout or API route if needed.
5. Notify affected customers if required.
6. Document root cause and corrective action.
