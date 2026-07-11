# Security Policy

## Supported Scope

Security review currently covers:

- `launch_site/` local/cloud-ready command center
- `nexus-saas/` Devvit app
- Resend waitlist notification integration
- Nexus Llama 3 backend chat integration
- Scraper-to-enrichment-to-sale-page workflow

## Reporting A Vulnerability

Do not open a public GitHub issue for sensitive security reports.

Send a private report to the project owner with:

- Affected component
- Steps to reproduce
- Impact
- Logs/screenshots with secrets redacted
- Suggested severity

## Launch-Blocking Issues

These block public launch:

- Auth bypass
- Cross-tenant or unauthorized data exposure
- Exposed API keys or secrets
- Raw private lead contact data published on public pages
- Unreviewed personal data sold or displayed
- Unsafe scraper behavior or source abuse
- Unauthorized location tracking
- Sensitive data in logs

## Secret Handling

Never commit:

- `RESEND_API_KEY`
- model provider keys
- storefront API keys
- private lead data
- local waitlist exports
- Reddit/Devvit credentials

