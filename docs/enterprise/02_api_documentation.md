# 02 API Documentation

Base production URL: `https://nexuscloud.sh`

Backend origin: `https://nexus-b2b-lead-generation.onrender.com`

All examples are representative. Secrets must never be sent from browser code.

## Health and Status

### `GET /healthz`

Render health check.

Response:

```json
{ "ok": true }
```

### `GET /api/health`

Application health/status endpoint.

Typical response includes runtime health and service readiness fields.

### `GET /api/revenue-status`

Returns storefront, Stripe, Resend, and lead-market readiness.

Response includes:

```json
{
  "ok": true,
  "resend": { "configured": true, "missing": [] },
  "stripe": { "configured": true, "missing": [], "catalogCount": 37 },
  "leadMarket": {
    "name": "HQ Florida leads",
    "availableCount": 137,
    "status": "For Sale"
  }
}
```

### `GET /api/fulfillment-status`

Returns paid-order fulfillment summary, recent events, test/blocked transactions, Stripe status, and Resend status.

Use this for dashboard monitoring.

## Lead and Enrichment APIs

### `POST /api/enrich-score`

Scores and enriches a lead payload.

Request:

```json
{
  "lead": {
    "company": "Example Realty",
    "market": "Tampa Bay",
    "source": "Approved public source",
    "signal": "Residential real estate opportunity"
  }
}
```

Response includes score, score band, reasons, confidence, next action, and storefront-safe fields.

### `POST /api/sale-listing`

Creates or refreshes a storefront-safe lead listing from scraper/enrichment output.

Request:

```json
{
  "lead": {
    "company": "Example Realty",
    "category": "Real estate",
    "city": "Tampa",
    "state": "FL"
  }
}
```

Response includes package fields suitable for public display without exposing raw sensitive data.

### `POST /api/osint-report`

Creates a safe OSINT/report preview for authorized report details.

Recommended use: paid lookup/report products after buyer intent is captured.

### `GET /api/scraper-queue`

Returns scraper queue/worker status for the command center.

### `GET /api/lead-stats`

Returns current lead inventory and quality metrics.

## Checkout and Fulfillment

### `POST /api/checkout`

Creates a Stripe Checkout session for a configured catalog item.

Request:

```json
{
  "priceId": "price_tb_leads_10_350"
}
```

Response:

```json
{
  "url": "https://checkout.stripe.com/..."
}
```

Notes:

- `STRIPE_SECRET_KEY` must be configured server-side.
- Stripe Prices can be resolved directly or by lookup key.
- Success URL uses `PUBLIC_BASE_URL`.

### `POST /api/stripe-webhook`

Receives Stripe webhook events.

Required header:

```text
Stripe-Signature: ...
```

Handled event:

```text
checkout.session.completed
```

Behavior:

1. Verifies Stripe signature.
2. Extracts checkout session and product metadata.
3. Records fulfillment event.
4. Sends buyer/admin email through Resend when configured.
5. Returns safe webhook response to Stripe.

### `POST /stripe/webhook`

Alias for `/api/stripe-webhook`.

## CRM APIs

### `GET /api/hubspot-status`

Alias: `GET /api/crm-status`

Returns HubSpot token/configuration status without exposing the token.

### `POST /api/hubspot-export`

Alias: `POST /api/crm-export`

Creates or updates a HubSpot contact.

Request:

```json
{
  "lead": {
    "email": "buyer@example.com",
    "contactName": "NEXUS Test Lead",
    "company": "NEXUS CRM Test",
    "phone": "727-555-0100",
    "website": "https://nexuscloud.sh",
    "city": "St Petersburg",
    "state": "FL",
    "postcode": "33709"
  }
}
```

Behavior:

1. Validates at least one contact/company identifier.
2. Searches HubSpot by email when email exists.
3. Patches existing contact or creates a new contact.
4. Records export metadata locally.

## AI Chat APIs

### `POST /api/chat`

NEXUS AI chat endpoint.

Request:

```json
{
  "prompt": "Show scraper and enrichment status"
}
```

Behavior:

- Uses `LLAMA_CHAT_ENDPOINT`, `LLAMA3_CHAT_ENDPOINT`, or `OLLAMA_HOST` when configured.
- Falls back to safe mode when no live endpoint is configured.

### `GET /api/chat-status`

Alias: `GET /api/llama-status`

Returns configured AI mode and missing endpoint variables.

## Waitlist and Events

### `POST /api/waitlist`

Stores a waitlist or buyer-intent submission and sends Resend notification when configured.

### `POST /api/lead-package-request`

Stores package request details for paid/pilot lead products.

### `POST /api/event`

Records frontend/operator event telemetry.

## API Security Notes

- Stripe and Resend secrets are server-only.
- HubSpot tokens are server-only.
- Webhook signatures are required for Stripe fulfillment.
- Public storefront responses should not expose raw personal data, sensitive identifiers, or unreviewed lead details.
- Add auth/RBAC before exposing administrative endpoints to third parties.
