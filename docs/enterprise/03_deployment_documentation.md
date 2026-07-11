# 03 Deployment Documentation

## Production Topology

| Layer | Current Setup |
| --- | --- |
| Domain | `nexuscloud.sh` |
| Edge | Cloudflare |
| Origin | Render `nexus-b2b-lead-generation` |
| Backend runtime | Python |
| Email | Resend |
| Payments | Stripe |
| CRM | HubSpot |
| CI/CD | GitHub Actions + Render auto-deploy/deploy hook |

## Render Setup

Primary service:

```text
Name: nexus-b2b-lead-generation
Service ID: srv-d91akdb7uimc73a2b8g0
URL: https://nexus-b2b-lead-generation.onrender.com
Root directory: backend
Runtime: Python
Build command: pip install -r requirements.txt
Start command: python main.py
Health check: /healthz
Region: Virginia
Plan: starter
```

Supporting services:

```text
nexus-tracking-api
nexus-osint-worker
```

## Cloudflare Setup

Current tunnel config:

```yaml
tunnel: c0301470-97c5-49ff-85e6-6ad1a7c39ea6
credentials-file: C:/Users/Robert/.cloudflared/c0301470-97c5-49ff-85e6-6ad1a7c39ea6.json

ingress:
  - hostname: nexuscloud.sh
    service: https://nexus-b2b-lead-generation.onrender.com
    originRequest:
      httpHostHeader: nexus-b2b-lead-generation.onrender.com
      originServerName: nexus-b2b-lead-generation.onrender.com
  - hostname: mail.nexuscloud.sh
    service: https://nexus-b2b-lead-generation.onrender.com
    originRequest:
      httpHostHeader: nexus-b2b-lead-generation.onrender.com
      originServerName: nexus-b2b-lead-generation.onrender.com
  - service: https://nexus-b2b-lead-generation.onrender.com
```

Validation:

```powershell
cloudflared tunnel --config "$env:USERPROFILE\.cloudflared\config.yml" ingress validate
```

Run tunnel:

```powershell
cloudflared tunnel --config "$env:USERPROFILE\.cloudflared\config.yml" run
```

Enterprise hardening:

- Install `cloudflared` as a Windows service or move to a managed Cloudflare DNS/custom-domain origin.
- Avoid dependence on an interactive desktop process.
- Add Cloudflare WAF rules, rate limiting, bot protection, and API path protections.

## Cloudflare Worker / Wrangler Setup

Worker project:

```text
deploy_artifacts/render-repo-work
```

Config:

```toml
name = "raspy-hat-15da"
compatibility_date = "2024-09-23"
main = "worker.js"

[assets]
directory = "frontend/dist"
binding = "ASSETS"
```

Build/dry-run:

```powershell
cd "deploy_artifacts\render-repo-work"
npx wrangler deploy --dry-run
```

Deploy:

```powershell
$env:CLOUDFLARE_API_TOKEN="..."
npx wrangler deploy
```

Note: this Worker currently serves static assets. Do not attach it to `nexuscloud.sh` unless API routing is intentionally designed.

## GitHub Actions CI/CD

Current workflows:

| Workflow | Purpose |
| --- | --- |
| `.github/workflows/ci.yml` | Launch-site smoke tests and Devvit build |
| `.github/workflows/security.yml` | CodeQL and dependency audit |
| `.github/workflows/package.yml` | Build/package deploy artifacts |
| `.github/workflows/deploy.yml` | Manual production deploy through Render deploy hook |

Recommended repository secrets:

| Secret | Purpose |
| --- | --- |
| `RENDER_DEPLOY_HOOK` | Manual production deployment |
| `CLOUDFLARE_API_TOKEN` | Worker/Cloudflare deploy automation |
| `STRIPE_SECRET_KEY` | Server-side checkout |
| `STRIPE_WEBHOOK_SECRET` | Webhook signature verification |
| `RESEND_API_KEY` | Email delivery |
| `HUBSPOT_ACCESS_TOKEN` or `HUBSPOT_SERVICE_KEY` | CRM export |

## Stripe Setup

Required environment variables:

```text
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
STRIPE_API_VERSION=2026-06-24.dahlia
PUBLIC_BASE_URL=https://nexuscloud.sh
```

Webhook endpoint:

```text
https://nexuscloud.sh/api/stripe-webhook
```

Primary event:

```text
checkout.session.completed
```

## Resend Setup

Required environment variables:

```text
RESEND_API_KEY
RESEND_FROM=NEXUS <no-reply@mail.nexuscloud.sh>
WAITLIST_NOTIFY_TO=burkefit2382@gmail.com
EMAIL_DOMAIN=mail.nexuscloud.sh
```

DNS records must be configured in Cloudflare exactly as Resend provides them. DKIM records should be DNS-only when required by Resend and should not be proxied if Resend instructs DNS-only.

## Environment Variables

| Variable | Required | Scope |
| --- | --- | --- |
| `PUBLIC_BASE_URL` | Yes | Checkout/email links |
| `STRIPE_SECRET_KEY` | Yes for payments | Checkout |
| `STRIPE_WEBHOOK_SECRET` | Yes for fulfillment | Webhook |
| `RESEND_API_KEY` | Yes for email | Email delivery |
| `RESEND_FROM` | Yes for email | Verified sender |
| `WAITLIST_NOTIFY_TO` or `RESEND_TO` | Yes for internal notifications | Email |
| `HUBSPOT_ACCESS_TOKEN` / `HUBSPOT_SERVICE_KEY` | Yes for CRM export | CRM |
| `HUBSPOT_PORTAL_ID` | Recommended | CRM dashboard links |
| `LLAMA_CHAT_ENDPOINT` | Optional | Live Llama 3 chat |
| `LLAMA_CHAT_MODEL` | Optional | Model selection |
| `EMAIL_DOMAIN` | Recommended | Sender fallback |

## Secrets Management

- Keep all provider keys in Render/GitHub/Cloudflare secret stores.
- Never commit `.env`, local JSONL data, API keys, screenshots of keys, or token values.
- Rotate any secret pasted into chat, screenshots, logs, or terminal captures.
- Separate production and staging secrets.
- Enable GitHub secret scanning and Dependabot alerts.
