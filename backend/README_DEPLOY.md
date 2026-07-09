# LeadGen Virtual Hub Launch Site Deployment

This folder contains the launch site plus a small Python backend for waitlist capture, AI demo endpoints, lead-package requests, and Stripe checkout.

## Local Preview

From this folder:

```powershell
python server.py
```

Open:

```text
http://127.0.0.1:4173/
```

## Windows + Cloudflare Tunnel

Use this when you want Stripe webhooks to reach the backend running on your Windows computer.

Terminal 1:

```powershell
cd "C:\Users\Robert\OneDrive\Imports\burkefit2382@gmail.com - Google Drive\Google AI Studio\launch_site"
python -m pip install -r requirements.txt
$env:LAUNCH_HOST = "127.0.0.1"
$env:PUBLIC_BASE_URL = "https://your-tunnel.trycloudflare.com"
$env:STRIPE_SECRET_KEY = "sk_test_or_live_xxxxxxxxx"
$env:STRIPE_WEBHOOK_SECRET = "whsec_xxxxxxxxx"
$env:RESEND_API_KEY = "re_xxxxxxxxx"
$env:RESEND_FROM = "NEXUS <no-reply@mail.nexuscloud.sh>"
$env:EMAIL_DOMAIN = "mail.nexuscloud.sh"
$env:WAITLIST_NOTIFY_TO = "you@yourdomain.com"
python server.py
```

Terminal 2:

```powershell
cloudflared tunnel --url http://127.0.0.1:4173
```

Copy the `https://...trycloudflare.com` URL from Cloudflare into `PUBLIC_BASE_URL` before starting checkout tests. In Stripe, create a webhook endpoint at:

```text
https://your-tunnel.trycloudflare.com/api/stripe-webhook
```

Enable `checkout.session.completed`.

## Emergent Route Fallback

Use these route rules for an Emergent/static SPA deployment:

```text
/ -> index.html
/styles.css -> styles.css
/app.js -> app.js
/dashboard -> dashboard.html
/(.*) -> index.html
```

The local Python server already applies the same fallback for unknown client routes.
For static hosts that support Netlify-style redirects, `_redirects` contains:

```text
/* /index.html 200
```

## Public Deployment

Deploy the contents of `launch_site/` as the site root. Use a Python-capable host when you need the `/api/*` endpoints.

### Render

1. Create a new Render web service.
2. Use `launch_site/` as the service root.
3. Render can read `render.yaml`.
4. Set these environment variables in Render:
   - `LAUNCH_HOST=0.0.0.0`
   - `RESEND_API_KEY`
   - `RESEND_FROM`
   - `EMAIL_DOMAIN=mail.nexuscloud.sh`
   - `WAITLIST_NOTIFY_TO`
   - `PUBLIC_BASE_URL=https://nexuscloud.sh`
   - `STRIPE_API_VERSION=2026-06-24.dahlia`
   - `STRIPE_SECRET_KEY`
   - `STRIPE_WEBHOOK_SECRET`
   - `HUBSPOT_ACCESS_TOKEN` for CRM contact export, or `HUBSPOT_PRIVATE_APP_TOKEN` / `HUBSPOT_API_KEY` as fallback names
   - `PRICE_ID` only if you want a default fallback price when no button price is sent
5. Health check path: `/healthz`.

### Railway

1. Create a new Railway service from this folder or upload the deploy zip.
2. Railway can read `railway.json`.
3. Set these variables:
   - `LAUNCH_HOST=0.0.0.0`
   - `RESEND_API_KEY`
   - `RESEND_FROM`
   - `EMAIL_DOMAIN=mail.nexuscloud.sh`
   - `WAITLIST_NOTIFY_TO`
   - `PUBLIC_BASE_URL=https://nexuscloud.sh`
   - `STRIPE_API_VERSION=2026-06-24.dahlia`
   - `STRIPE_SECRET_KEY`
   - `STRIPE_WEBHOOK_SECRET`
   - `HUBSPOT_ACCESS_TOKEN` for CRM contact export, or `HUBSPOT_PRIVATE_APP_TOKEN` / `HUBSPOT_API_KEY` as fallback names
   - `PRICE_ID` only if you want a default fallback price when no button price is sent
4. Railway provides `PORT`; `server.py` reads it automatically.

Required before public launch:

- Connect the pilot form to a real backend, CRM, spreadsheet, storefront workflow, or email capture provider.
- Keep email and payment provider secrets server-side. Do not put Resend or Stripe secret keys in browser code.
- Publish reviewed privacy policy and terms links.
- Replace prototype-only form message with real success/failure handling.
- Confirm domain, SSL, analytics, and support contact.
- Confirm public claims match actual product evidence.

## Static Assets

- `index.html`: landing page
- `dashboard.html`: dedicated command dashboard served at `/dashboard`
- `styles.css`: responsive styling
- `app.js`: prototype waitlist form behavior using local browser storage
- `server.py`: local static server with `POST /api/waitlist`
- `/api/chat`: optional Nexus Llama 3 chat endpoint with safe fallback mode
- `/api/enrich-score`: demo AI enrichment and scoring endpoint for scraped leads
- `/api/sale-listing`: demo endpoint that converts enriched lead output into a storefront-safe lead package
- `/api/revenue-status`: revenue readiness and HQ Florida lead package status
- `/api/lead-package-request`: buyer package request capture for HQ Florida leads
- `/api/checkout`: Stripe Checkout session creation for configured pricing catalog items
- `/api/stripe-webhook`: signed Stripe webhook handler for automatic fulfillment logging and Resend delivery
- `render.yaml`: Render web service blueprint
- `railway.json`: Railway deployment config
- `vercel.json`: static rewrites and headers for Vercel-style static hosting
- `staticwebapp.config.json`: static rewrites and headers for Azure Static Web Apps-style hosting
- `.env.example`: local environment variable template
- `assets/dashboard-preview.png`: generated product preview image
- `_headers`: recommended static security headers for hosts that support them
- `_redirects`: static host fallback so `/` and deep routes load `index.html`

## Resend Waitlist Notifications

The local Python server can send waitlist notifications through Resend when the `resend` package and environment variables are configured.

Before enabling Resend in production:

1. In Resend, add a sending subdomain such as `mail.nexuscloud.sh`; Resend recommends a subdomain instead of the root domain for deliverability.
2. Copy the DKIM and SPF DNS records from the Resend domain Records tab into your DNS host exactly as generated.
3. Wait for verification. Resend says verification often completes within about 15 minutes, but DNS propagation can take up to 72 hours.
4. Add a DMARC record after the domain verifies.
5. Use a sender address on that verified subdomain, such as `NEXUS <no-reply@mail.nexuscloud.sh>`.

Install from this folder:

```powershell
python -m pip install -r requirements.txt
```

Additional backend-side Resend utilities are in:

```text
../integrations/resend/
```

Use Resend from a serverless function or backend route, not directly from browser JavaScript.

For local testing, `server.py` calls the Resend helper when these environment variables are configured:

```powershell
$env:RESEND_API_KEY = "re_xxxxxxxxx"
$env:RESEND_FROM = "NEXUS <no-reply@mail.nexuscloud.sh>"
$env:EMAIL_DOMAIN = "mail.nexuscloud.sh"
$env:WAITLIST_NOTIFY_TO = "you@yourdomain.com"
python server.py
```

Without those variables, submissions are still stored locally in:

```text
../data/waitlist_requests.jsonl
```

## Nexus Llama 3 Chat

The command-center chat works in safe fallback mode by default.

To connect a local Ollama-compatible Llama 3 endpoint:

```powershell
$env:LLAMA_CHAT_ENDPOINT = "http://127.0.0.1:11434/api/chat"
$env:LLAMA_CHAT_MODEL = "llama3"
python server.py
```

For cloud hosting, set `LLAMA_CHAT_ENDPOINT` to your hosted Llama-compatible chat API. Optional bearer auth is read from `LLAMA_CHAT_API_KEY`, `LLAMA_API_KEY`, or `LLAMA3_API_KEY`. Nexus also accepts `LLAMA3_CHAT_ENDPOINT` and `OLLAMA_HOST` as endpoint aliases. Do not put model API keys in browser code.

## Stripe Checkout

The pricing and marketplace buttons call `POST /api/checkout` with a catalog `priceId`.

For local testing after rotating any exposed key:

```powershell
$env:PUBLIC_BASE_URL = "https://nexuscloud.sh"
$env:STRIPE_API_VERSION = "2026-06-24.dahlia"
$env:STRIPE_SECRET_KEY = "your_rotated_stripe_secret_key"
python server.py
```

The backend accepts these catalog lookup keys:

```text
price_starter_350
price_pro_700
price_elite_1000
price_dfy_997
price_dfy_setup_1500
price_tb_leads_10_350
price_tb_leads_25_700
price_tb_leads_50_1000
price_lead_verify_plan_99
price_lead_verify_plan_299
price_lead_verify_plan_499
price_osint_basic
price_osint_deep
price_osint_homeowner
price_intel_market
price_intel_neighborhood
price_intel_competitor
```

Create Stripe Prices with those lookup keys, or update `STRIPE_CATALOG` in `server.py` with the real Stripe `price_...` IDs. `PRICE_ID` is optional because browser buttons send their catalog key to `/api/checkout`.

## Automatic Fulfillment

Configure a Stripe webhook endpoint:

```text
https://nexuscloud.sh/api/stripe-webhook
```

If you deploy the backend on an API subdomain, this alias is also supported:

```text
https://api.nexuscloud.sh/stripe/webhook
```

Enable this event:

```text
checkout.session.completed
```

Set the webhook signing secret in the backend:

```powershell
$env:STRIPE_WEBHOOK_SECRET = "your_stripe_webhook_secret"
```

When a paid checkout completes, the backend records a fulfillment event in:

```text
../data/fulfillment_events.jsonl
```

If Resend is configured, the backend sends a buyer confirmation and an internal paid-order alert. If Resend is missing, the event is logged as `pending_manual_delivery`.
