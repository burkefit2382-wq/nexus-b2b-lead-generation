# API Reference

All API routes are served by `server.py`.

## Health

`GET /healthz`

Returns service health for Render and uptime checks.

## Revenue And Dashboard

`GET /api/revenue-status`

Returns configured revenue readiness, package status, and current HQ lead market data.

`GET /api/fulfillment-events`

Returns masked fulfillment events for dashboard display.

## Checkout

`POST /api/checkout`

Request:

```json
{ "priceId": "price_starter_350" }
```

Creates a Stripe Checkout Session for a catalog item. Unknown catalog keys return `400` so retired low-price buttons cannot be used.

`POST /api/stripe-webhook`

Receives signed Stripe webhook events. `checkout.session.completed` creates a fulfillment record and triggers Resend notifications when configured.

## Lead Workflow

`POST /api/enrich-score`

Accepts scraped lead samples and returns enriched demo scoring output.

`GET /api/sale-listing`

Returns a storefront-safe listing generated from enriched lead package output.

`POST /api/lead-package-request`

Captures lead package request metadata and sends an internal notification when Resend is configured.

## HubSpot CRM

`GET /api/hubspot-status`

Returns whether `HUBSPOT_ACCESS_TOKEN` is configured.

`POST /api/hubspot-export`

Exports one reviewed Nexus lead as a HubSpot CRM contact. If an email is provided, Nexus searches HubSpot by email and updates the existing contact; otherwise it creates a contact.

Request:

```json
{
  "lead": {
    "email": "agent@example.com",
    "contactName": "Demo Agent",
    "company": "NEXUS Tampa Bay Pilot",
    "phone": "+1-727-555-0199",
    "website": "https://nexuscloud.sh",
    "city": "St Petersburg",
    "state": "FL",
    "postcode": "33709"
  }
}
```

Requires a HubSpot private app token with contact read/write permissions.

## OSINT

`POST /api/osint-report`

Creates a safe OSINT report request preview and appends the request to the operational queue. Requests for live location tracking, credential theft, hacking, bypassing protections, or stalking are blocked.

## AI Chat

`POST /api/chat`

Uses a configured Llama-compatible endpoint when `LLAMA_CHAT_ENDPOINT` is set. Falls back to safe local responses when no endpoint is configured.
