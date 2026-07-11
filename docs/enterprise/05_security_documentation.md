# 05 Security Documentation

## Current Security Posture

NEXUS has a strong launch-oriented foundation: Cloudflare edge routing, HTTPS, Stripe webhook signature verification, server-side secrets, GitHub security workflows, and dashboard masking for buyer email data.

This is not yet an audited compliance certification. Treat this document as a control map and hardening plan.

## Current Controls

| Area | Current Control |
| --- | --- |
| TLS/SSL | Cloudflare and Render HTTPS |
| Webhook integrity | Stripe signature verification |
| Secret handling | Provider keys read from environment variables |
| Email safety | Resend runs server-side only |
| CRM token safety | HubSpot token stays server-side |
| Dashboard privacy | Fulfillment dashboard masks buyer email details |
| CI security | CodeQL and dependency audit workflow present |
| Dependency hygiene | Python `pip-audit` workflow present |
| Data minimization | Public storefront listings avoid raw phone/email exposure |

## Cloudflare Security Plan

Recommended configuration:

| Feature | Recommended Use |
| --- | --- |
| WAF | Protect `/api/*`, `/dashboard`, `/lead-control-center` |
| Bot protection | Challenge abusive traffic and known automation |
| Rate limiting | Apply limits to checkout, CRM export, chat, and enrichment endpoints |
| Turnstile | Add to waitlist, lead package request, and report request forms |
| Access / Zero Trust | Protect admin-only dashboards and internal tools |
| DNSSEC | Enable for domain trust |
| Security headers | Enforce HSTS, X-Content-Type-Options, Referrer-Policy, frame controls |

## API Gateway Controls

Recommended policy:

- Public: `GET /`, `GET /dashboard`, public static files, `POST /api/waitlist`, `POST /api/checkout`.
- Protected/admin: CRM export, fulfillment inspection, lead inventory detail, scraper controls.
- Webhook-only: `/api/stripe-webhook`, validated by Stripe signature.
- Rate-limited: chat, enrichment, OSINT report generation, package request endpoints.

## Secrets Management

Required rules:

- No provider secrets in Git.
- No secrets in frontend JS or HTML.
- No secrets in logs or screenshots.
- Rotate any token pasted into chat or shown in a screenshot.
- Store production secrets only in Render/GitHub/Cloudflare secret stores.
- Separate local, staging, and production secrets.

## Input Validation

Current validation exists for:

- Stripe catalog price IDs.
- Stripe webhook signatures.
- HubSpot export minimum identifier.
- HubSpot email format.
- Safe storefront field generation.

Recommended additions:

- Central request schema validation.
- Strict max body sizes.
- URL allowlist for scraper/OSINT sources.
- Email and phone normalization.
- CSRF protection for authenticated dashboards.
- Auth checks for CRM export and admin routes.

## OWASP Launch Checklist

| Risk | Status | Next Step |
| --- | --- | --- |
| Injection | Needs formal testing | Add automated fuzz tests for API payloads |
| XSS | Needs browser test pass | Validate DOM rendering and escaping |
| CSRF | Needs auth model | Add CSRF once authenticated sessions exist |
| Broken auth | Open | Add login, RBAC, MFA for admin surfaces |
| Sensitive data exposure | Partial | Move JSONL logs to durable encrypted storage |
| Security misconfiguration | Partial | Lock Cloudflare/RBAC, headers, WAF |
| Logging/monitoring | Partial | Add central logs and alerts |

## Government/Enterprise Readiness Gap

Before presenting as government-grade:

- Add RBAC and MFA.
- Add audit logging.
- Add retention policy enforcement.
- Add incident response procedure.
- Add vulnerability management evidence.
- Add penetration test or third-party security review.
- Add data processing agreements and privacy policy.
- Add backup/restore testing.

## Security Evidence to Maintain

- Dependency scan results.
- Secret scan results.
- API smoke test results.
- Stripe webhook test evidence.
- Cloudflare WAF/rate-limit configuration exports.
- Incident response drill notes.
- Access-control review.
- Data-retention review.
