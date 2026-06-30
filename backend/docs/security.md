# Security

## Current Controls

- Server-side Stripe Checkout only. Secret keys are never placed in frontend code.
- Stripe webhook signature verification before fulfillment processing.
- Resend runs server-side only.
- Unsafe OSINT requests are blocked before queueing.
- Dashboard fulfillment responses mask buyer email addresses.
- Static security headers are included in `_headers`, `vercel.json`, and `staticwebapp.config.json`.
- Unknown or retired catalog price IDs are rejected by `/api/checkout`.

## Required Operational Practices

- Rotate any secret that was ever shared in screenshots, chat, logs, or commits.
- Use separate test and live Stripe keys.
- Keep Render, Cloudflare, Stripe, Resend, and domain accounts protected with MFA.
- Treat lead data as sensitive business data.
- Do not sell or expose raw personal data unless collection, use, and delivery comply with applicable law and platform terms.
- Use reviewed privacy policy, terms, refund policy, and acceptable-use language before scaling paid traffic.

## Enterprise Hardening Backlog

- Add authentication and role-based access control.
- Move JSONL logs to PostgreSQL with row-level ownership.
- Add immutable audit logging.
- Add rate limits for public APIs.
- Add request IDs and structured security logging.
- Add data retention and deletion workflows.
- Add dependency scanning and secret scanning.
- Add backup and restore runbooks.

