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

Returns whether a HubSpot token is configured. Nexus checks `HUBSPOT_ACCESS_TOKEN`, `HUBSPOT_SERVICE_KEY`, `HUBSPOT_PRIVATE_APP_TOKEN`, then `HUBSPOT_API_KEY`. The response also includes the public HubSpot portal ID and embed script URL.

Alias: `GET /api/crm-status`

`POST /api/hubspot-export`

Exports one reviewed Nexus lead as a HubSpot CRM contact. If an email is provided, Nexus searches HubSpot by email and updates the existing contact; otherwise it creates a contact.

Alias: `POST /api/crm-export`

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

`GET /api/chat-status`

Returns whether a server-side Llama 3 endpoint is configured. Nexus checks `LLAMA_CHAT_ENDPOINT`, `LLAMA3_CHAT_ENDPOINT`, then `OLLAMA_HOST`.

Alias: `GET /api/llama-status`

`POST /api/chat`

Uses a configured Llama-compatible endpoint when available. Supports Ollama-style `/api/chat` responses, OpenAI-compatible `choices[].message.content` responses, and a safe local fallback when no endpoint is configured.
