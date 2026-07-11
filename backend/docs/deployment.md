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
LLAMA_CHAT_API_KEY=...
HUBSPOT_PRIVATE_APP_TOKEN=...
HUBSPOT_PORTAL_ID=246668830
```

### GitHub-triggered redeploys

This repo includes `.github/workflows/render-backend-redeploy.yml` for branch-based promotion and manual promotion across environments:

- `develop` -> Development deploy hooks
- `staging` -> Staging deploy hooks
- `main` -> Production deploy hooks
- `workflow_dispatch` -> manual deploy to `dev`, `staging`, or `prod`

Configure these GitHub repository secrets before relying on the workflow:

```text
RENDER_DEV_LAUNCH_SITE_DEPLOY_HOOK=https://api.render.com/deploy/...
RENDER_DEV_TRACKING_API_DEPLOY_HOOK=https://api.render.com/deploy/...
RENDER_STAGING_LAUNCH_SITE_DEPLOY_HOOK=https://api.render.com/deploy/...
RENDER_STAGING_TRACKING_API_DEPLOY_HOOK=https://api.render.com/deploy/...
RENDER_PROD_LAUNCH_SITE_DEPLOY_HOOK=https://api.render.com/deploy/...
RENDER_PROD_TRACKING_API_DEPLOY_HOOK=https://api.render.com/deploy/...
```

Create one deploy hook per Render service per environment, then store each hook URL in its matching GitHub secret. The workflow always runs backend compile checks and pytest first, then triggers the environment hooks.

For safer promotion, add GitHub environment protection rules on `Development`, `Staging`, and `Production` (for example required reviewers before Production deploys).

## HubSpot CRM

Create a HubSpot private app and grant contact read/write scopes. Set the token in Render using `HUBSPOT_PRIVATE_APP_TOKEN`. Nexus also accepts `HUBSPOT_ACCESS_TOKEN`, `HUBSPOT_SERVICE_KEY`, or `HUBSPOT_API_KEY` as fallback names for existing environments. Set `HUBSPOT_PORTAL_ID=246668830` for dashboard visibility and the HubSpot embed script.

Nexus sends the token only from the server using a Bearer Authorization header. Contact export is active through `/api/hubspot-export`; inbound HubSpot webhooks require a separate webhook route before they can receive HubSpot events.

## Llama 3 Chat

Set `LLAMA_CHAT_ENDPOINT` to a hosted Llama-compatible chat endpoint, or set `OLLAMA_HOST` for an Ollama server and Nexus will call `/api/chat` automatically. Optional bearer auth can be supplied with `LLAMA_CHAT_API_KEY`.

Accepted fallback names:

```text
LLAMA3_CHAT_ENDPOINT
LLAMA3_CHAT_MODEL
LLAMA_API_KEY
LLAMA3_API_KEY
OLLAMA_HOST
OLLAMA_MODEL
```

The browser never receives the Llama API key. The frontend calls `/api/chat`; the backend calls the model endpoint.

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
