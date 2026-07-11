# HubSpot Integration Guide

## Canonical authentication

Use **`HUBSPOT_PRIVATE_APP_TOKEN`** as the authoritative production secret.

Backward-compatible fallback names remain supported for existing deployments:

- `HUBSPOT_ACCESS_TOKEN`
- `HUBSPOT_SERVICE_KEY`
- `HUBSPOT_API_KEY`

## Required setup

1. Create a HubSpot private app.
2. Grant at least contact read/write scopes.
3. Store the token in Render as `HUBSPOT_PRIVATE_APP_TOKEN`.
4. Set `HUBSPOT_PORTAL_ID` for dashboard links/visibility.

## Runtime behavior

- CRM sync uses server-side bearer auth only.
- Calls retry with bounded exponential backoff on 429 and 5xx responses.
- Legacy token env vars are still read so existing environments do not break.
- HubSpot sync failures must not block core lead capture or checkout completion; the app logs the issue and continues.

## Verification

- Call `/api/hubspot-status` and verify `configuredBy` and `canonicalTokenName`.
- Run a test export through `/api/hubspot-export` using a non-production contact.
- Confirm rate-limit or transport failures surface as sanitized errors without leaking the token.
