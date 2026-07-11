# Stripe Integration Guide

## Required environment variables

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_API_VERSION`
- `PRICE_ID`
- `PUBLIC_BASE_URL`

## Hardening requirements

- Webhook handlers must reject unsigned or invalid payloads.
- Payment-creating requests must send Stripe idempotency keys.
- `STRIPE_API_VERSION` must remain pinned and only change as part of an explicit upgrade test cycle.
- Logs must not contain full payment payloads, PAN, or customer-sensitive billing details.

## Webhook setup

1. Create the webhook endpoint in Stripe for the production Render or Cloudflare-routed origin.
2. Subscribe at minimum to:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
3. Copy the webhook signing secret into `STRIPE_WEBHOOK_SECRET`.

## Verification

- Use Stripe test mode to create a checkout session.
- Replay a signed webhook from the Stripe dashboard or CLI.
- Confirm the webhook is rejected when the signature header is missing or invalid.

## Upgrade procedure

1. Pin the new `STRIPE_API_VERSION` in code and Render.
2. Re-run backend tests and webhook smoke tests.
3. Confirm checkout/session creation still succeeds with idempotency enabled.
4. Deploy to staging before production.
