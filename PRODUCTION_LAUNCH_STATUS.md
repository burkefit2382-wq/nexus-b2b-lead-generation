# Production Launch Status

Last updated: 2026-06-29

## Live URLs

- Public command center: https://nexuscloud.sh/
- Public dashboard: https://nexuscloud.sh/dashboard
- Render command center: https://nexus-b2b-lead-generation.onrender.com/
- Render dashboard: https://nexus-b2b-lead-generation.onrender.com/dashboard
- Revenue storefront: https://nexuscloud.sh/#lead-market
- Pricing: https://nexuscloud.sh/#pricing
- Product marketplace: https://nexuscloud.sh/#marketplace
- Devvit playtest: https://www.reddit.com/r/nexus_saas_dev/?playtest=nexus-saas

## Verified Working

- Static routing:
  - `/` -> `index.html`
  - `/styles.css` -> `styles.css`
  - `/app.js` -> `app.js`
  - `/dashboard` -> `dashboard.html`
  - unknown routes -> `index.html`
- Public APIs:
  - `POST /api/revenue-status`
  - `POST /api/sale-listing`
  - `POST /api/lead-package-request`
  - `POST /api/checkout`
  - `POST /api/stripe-webhook`
  - `POST /api/chat`
  - `POST /api/enrich-score`
  - `POST /api/waitlist`
- Pricing and paid catalog:
  - Starter, Pro, Elite, and DFY SaaS plans are listed.
  - Lead bundles, OSINT reports, and AI intelligence reports are listed.
  - Stripe Checkout creates live checkout sessions for subscription and one-time catalog items.
  - DFY checkout includes the one-time setup fee plus monthly subscription.
- HQ Florida storefront:
  - 137 available leads
  - 10 leads for $49
  - 25 leads for $99
  - 50 leads for $149
- Buyer package requests are stored locally in `data/lead_package_requests.jsonl`.
- Stripe checkout completion events are stored locally in `data/fulfillment_events.jsonl`.
- Resend SDK is installed.
- Stripe SDK is installed.
- Stripe webhook signature verification is active for `checkout.session.completed`.
- Fulfillment dashboard is visible on `/dashboard`.
- Render production service is live and serving the Nexus launch app.
- Devvit type-check and build pass.
- Python server compile passes.

## Production Blocks Before Taking Paid Orders

- Set `RESEND_API_KEY`.
- Set `RESEND_FROM` using a verified Resend domain.
- Set `WAITLIST_NOTIFY_TO` or `RESEND_TO`.
- Restore a valid backend `STRIPE_SECRET_KEY` if checkout reports setup-needed.
- Set Render `RESEND_API_KEY` after creating a valid Resend production key.
- Connect a durable production database or CRM instead of local JSONL files.
- Push this workspace to GitHub/GitHub Enterprise and enable branch protection.
- Confirm Cloudflare Tunnel is managed as a Windows service or by a supervised process.

## Current Launch Decision

Public demo, buyer-intent capture, Stripe payment collection, and webhook fulfillment logging are live. Buyer email delivery is wired but will remain pending/manual until Resend secrets are configured.
