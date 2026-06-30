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
```

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

