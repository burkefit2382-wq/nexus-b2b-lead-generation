# Deployment

## Render

This repo is deployed as a Render web service.

Recommended settings:

```text
Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: python main.py
Health Check Path: /healthz
```

Required environment variables:

```text
LAUNCH_HOST=0.0.0.0
PUBLIC_BASE_URL=https://nexuscloud.sh
STRIPE_SECRET_KEY=...
STRIPE_WEBHOOK_SECRET=...
RESEND_API_KEY=...
RESEND_FROM=Nexus <sales@nexuscloud.sh>
WAITLIST_NOTIFY_TO=...
LLAMA_CHAT_ENDPOINT=...
LLAMA_CHAT_MODEL=llama3
HUBSPOT_ACCESS_TOKEN=...
HUBSPOT_PORTAL_ID=...
```

## HubSpot CRM

Create a HubSpot private app or service key and grant contact read/write scopes. Set the token in Render using `HUBSPOT_ACCESS_TOKEN`. Nexus also accepts `HUBSPOT_PRIVATE_APP_TOKEN` or `HUBSPOT_API_KEY` as fallback names, which helps when Render already has those environment variables from setup notes. Set `HUBSPOT_PORTAL_ID` for dashboard visibility.

Nexus sends the token only from the server using a Bearer Authorization header. Contact export is active through `/api/hubspot-export`; inbound HubSpot webhooks require a separate webhook route before they can receive HubSpot events.

## Cloudflare Tunnel

For a local production-style tunnel, point Cloudflare to the running Python service:

```text
url: http://localhost:4174
```

Start the local service with production environment variables loaded and `PUBLIC_BASE_URL=https://nexuscloud.sh`.

## Static Routing

Use these fallbacks on static hosts:

```text
/ -> index.html
/styles.css -> styles.css
/app.js -> app.js
/dashboard -> dashboard.html
/(.*) -> index.html
```

## Stripe Webhook

Webhook endpoint:

```text
https://nexuscloud.sh/api/stripe-webhook
```

Required event:

```text
checkout.session.completed
```

Store the webhook signing secret as `STRIPE_WEBHOOK_SECRET`.
