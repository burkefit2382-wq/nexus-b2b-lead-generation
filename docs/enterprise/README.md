# NEXUS Enterprise Documentation Bundle

Last updated: 2026-07-11

This bundle documents the current NEXUS Lead Intelligence SaaS for launch, buyer review, operator handoff, and enterprise-readiness conversations.

## Documents

| Document | Purpose |
| --- | --- |
| [01 Architecture Overview](01_architecture_overview.md) | End-to-end system overview and component map |
| [02 API Documentation](02_api_documentation.md) | Public/backend endpoints, request shapes, and responses |
| [03 Deployment Documentation](03_deployment_documentation.md) | Cloudflare, Render, GitHub Actions, Stripe, env vars, and secrets |
| [04 CRM Integration](04_crm_integration.md) | HubSpot/CRM sync, lead delivery, subscriptions, and email automation |
| [05 Security Documentation](05_security_documentation.md) | Current controls, security posture, and hardening roadmap |
| [06 Data Flow](06_data_flow.md) | LeadGen, OSINT, real estate, AI enrichment, and report-generation flows |
| [07 Buyer Transfer](07_buyer_transfer.md) | Transfer steps for domain, Cloudflare, Render, Stripe, CRM, and GitHub |
| [08 SLA and Uptime](08_sla_uptime.md) | Health checks, uptime model, incident targets, and monitoring |
| [09 Market Appraisal](09_market_appraisal.md) | Internal valuation framing and value drivers |
| [10 Launch Checklist](10_launch_checklist.md) | Final practical launch gates |

## Current Verified Production URLs

| Surface | URL |
| --- | --- |
| Public command center | https://nexuscloud.sh/ |
| Dashboard | https://nexuscloud.sh/dashboard |
| Lead marketplace | https://nexuscloud.sh/#lead-market |
| Pricing | https://nexuscloud.sh/#pricing |
| Render backend | https://nexus-b2b-lead-generation.onrender.com/ |
| Tracking API | https://nexus-tracking-api.onrender.com/ |

## Current Launch Status

- Render production backend is live.
- Cloudflare Tunnel routes `nexuscloud.sh` and `mail.nexuscloud.sh` to the Render production backend.
- Stripe checkout and webhook configuration report as configured.
- Resend email delivery reports as configured.
- HubSpot CRM endpoints exist and require a valid server-side token for live export.
- Local JSONL storage is still used for some operational logs; durable database/CRM storage is the next enterprise hardening item.

## Claim Discipline

Use this package as a professional documentation set, not as a compliance certification. Do not claim SOC 2, HIPAA, FedRAMP, or audited government-grade compliance until independent evidence and controls are complete.
