# Deployment

## Azure Primary

Azure is the primary production deployment path.

The repository uses Azure Developer CLI (`azd`) to provision and deploy:

- Python App Service for the backend
- Azure Static Web App for the frontend

Key files:

```text
azure.yaml
infra/main.bicep
infra/resources.bicep
infra/main.parameters.json
.github/workflows/azure-dev.yml
```

Primary workflow:

```text
.github/workflows/azure-dev.yml
```

Required GitHub repository variables:

```text
AZURE_CLIENT_ID
AZURE_TENANT_ID
AZURE_SUBSCRIPTION_ID
AZURE_ENV_NAME
AZURE_LOCATION
```

Required GitHub repository secrets:

```text
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
PRICE_ID
DATABASE_URL
RESEND_API_KEY
RESEND_FROM
WAITLIST_NOTIFY_TO
HUBSPOT_ACCESS_TOKEN
HUBSPOT_PORTAL_ID
```

The Azure Bicep template applies these values as App Service runtime settings during provision. It also sets `PUBLIC_BASE_URL` and `TRACKING_ALLOWED_ORIGIN` from the Azure Static Web App hostname, while the GitHub workflow builds the frontend with `VITE_API_BASE_URL=https://api-${AZURE_ENV_NAME}.azurewebsites.net`.

## Render Fallback

Render remains available as a fallback web service, not the primary deployment path.

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
PRICE_ID=...
DATABASE_URL=...
RESEND_API_KEY=...
RESEND_FROM=Nexus <sales@nexuscloud.sh>
WAITLIST_NOTIFY_TO=...
LLAMA_CHAT_ENDPOINT=...
LLAMA_CHAT_MODEL=llama3
LLAMA_CHAT_API_KEY=...
HUBSPOT_ACCESS_TOKEN=...
HUBSPOT_SERVICE_KEY=...
HUBSPOT_PORTAL_ID=246668830
```

### Manual GitHub-triggered redeploy

This repo includes `.github/workflows/deploy-backend.yml` for manual Render fallback deploys.

Configure these GitHub repository secrets before relying on the fallback workflow:

```text
RENDER_API_KEY
RENDER_SERVICE_ID
```

The workflow runs backend compile checks and pytest first, then calls the Render Deploy API.

## HubSpot CRM

Create a HubSpot private app or service key and grant contact read/write scopes. Set the token in Azure using `HUBSPOT_ACCESS_TOKEN` or `HUBSPOT_SERVICE_KEY`; for the Render fallback, use the same names. Nexus also accepts `HUBSPOT_PRIVATE_APP_TOKEN` or `HUBSPOT_API_KEY` as fallback names, which helps when a host already has those environment variables from setup notes. Set `HUBSPOT_PORTAL_ID=246668830` for dashboard visibility and the HubSpot embed script.

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
