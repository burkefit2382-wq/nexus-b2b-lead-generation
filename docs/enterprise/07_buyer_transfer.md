# 07 Buyer Transfer Documentation

## Purpose

This document explains how to transfer NEXUS operational ownership to a buyer, partner, or new operator.

Do not transfer secrets through email or chat. Use provider account transfer features or rotate secrets after handoff.

## Transfer Order

Recommended order:

1. GitHub repository
2. Render services
3. Cloudflare domain/DNS/Tunnel
4. Stripe account/products/webhooks
5. Resend domain/API keys
6. HubSpot CRM
7. Operational runbooks and data exports
8. Final secret rotation

## GitHub Transfer

Assets:

- Repository: `burkefit2382-wq/nexus-b2b-lead-generation`
- Branches: `main`, `master`, and multiple Copilot work branches
- Workflows: CI, security, packaging, deployment

Steps:

1. Add buyer as repository admin or transfer repository ownership.
2. Confirm buyer can clone and run CI.
3. Recreate repository secrets in buyer account.
4. Enable branch protection.
5. Enable secret scanning and Dependabot.
6. Remove seller access after acceptance.

## Render Transfer

Services:

- `nexus-b2b-lead-generation`
- `nexus-tracking-api`
- `nexus-osint-worker`

Steps:

1. Invite buyer to Render workspace.
2. Confirm billing transfer.
3. Confirm each service uses the intended GitHub repository and branch.
4. Export environment variable names, not secret values.
5. Buyer creates fresh secrets.
6. Trigger a deploy.
7. Verify `/healthz`, `/api/revenue-status`, and `/api/fulfillment-status`.

## Cloudflare Transfer

Assets:

- Domain: `nexuscloud.sh`
- Tunnel: `c0301470-97c5-49ff-85e6-6ad1a7c39ea6`
- Hostnames: `nexuscloud.sh`, `mail.nexuscloud.sh`
- Resend DNS records

Steps:

1. Transfer domain or add buyer to Cloudflare account.
2. Confirm DNS records.
3. Confirm SSL/TLS mode.
4. Confirm Tunnel ingress points to production Render backend.
5. Install tunnel as a service or replace with durable custom-domain routing.
6. Rotate Cloudflare API tokens.
7. Revoke seller API tokens.

## Stripe Transfer

Assets:

- Products/prices for SaaS tiers, lead bundles, scan credits, reports, DFY offers
- Webhook endpoint: `https://nexuscloud.sh/api/stripe-webhook`
- Checkout session backend integration

Steps:

1. Transfer account ownership or recreate products in buyer Stripe account.
2. Export product/price catalog.
3. Recreate webhook endpoint.
4. Set new `STRIPE_SECRET_KEY`.
5. Set new `STRIPE_WEBHOOK_SECRET`.
6. Test checkout in test mode.
7. Switch live mode after validation.

## Resend Transfer

Assets:

- Sending domain: `mail.nexuscloud.sh`
- Sender: `NEXUS <no-reply@mail.nexuscloud.sh>`

Steps:

1. Transfer or recreate Resend domain.
2. Confirm DNS records in Cloudflare.
3. Create fresh production API key.
4. Set `RESEND_API_KEY`, `RESEND_FROM`, and notification recipient variables in Render.
5. Send test delivery.
6. Revoke old API keys.

## HubSpot CRM Transfer

Assets:

- Portal ID: `246668830`
- Contact export endpoints
- Forms, workflows, tasks, properties

Steps:

1. Add buyer as HubSpot super admin or export/import CRM configuration.
2. Create buyer-owned private app token/service key.
3. Set CRM token in Render.
4. Confirm contact upsert.
5. Confirm workflows/tasks.
6. Remove seller access.

## Data Transfer

Data types:

- Fulfillment events
- Lead package requests
- Waitlist submissions
- CRM export logs
- Lead datasets
- Reports and pilot packs

Rules:

- Remove personal/sensitive data not required for sale.
- Transfer only data the buyer is legally allowed to receive.
- Provide data dictionary and retention schedule.
- Prefer encrypted export storage.

## Final Handoff Checklist

- Buyer owns domain or has Cloudflare admin.
- Buyer owns Render services and billing.
- Buyer owns GitHub repo.
- Buyer owns Stripe account/products/webhooks.
- Buyer owns Resend sending domain/API key.
- Buyer owns CRM/private app token.
- All old secrets rotated.
- Seller API tokens revoked.
- Production smoke test passes.
