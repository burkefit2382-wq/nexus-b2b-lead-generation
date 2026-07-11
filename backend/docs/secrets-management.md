# Secrets Management Guide

## Secret locations

- **Render**: runtime environment variables for backend services
- **GitHub Actions**: deploy hooks, Cloudflare credentials, Neon credentials, environment-scoped secrets
- **Cloudflare**: Worker/account credentials and any edge-side secrets

## Policy

- Never commit secrets to `.env`, `.neon`, JSON fixtures, or workflow files.
- Keep production secrets in environment-scoped stores with least-privilege access.
- Rotate Stripe, Resend, HubSpot, Neon, and Cloudflare credentials on a regular schedule and after any suspected exposure.
- Prefer private app tokens / scoped API tokens over broad legacy keys.

## Operational checklist

- Use `.env.example` for placeholders only.
- Scan changed files for secrets before every commit.
- Keep production secrets out of browser code and static bundles.
- Review GitHub environment protections and secret access quarterly.
