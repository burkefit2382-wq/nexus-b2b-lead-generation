# Security Policy

## Reporting Security Issues

Do not open public GitHub issues for vulnerabilities or exposed secrets.

Send security reports to the repository owner through the private support channel configured for the deployment.

Include:

- Affected URL or endpoint
- Steps to reproduce
- Potential impact
- Screenshots or logs with secrets redacted

## Supported Version

The `main` branch is the supported production branch.

## Secret Handling

Never commit:

- Stripe secret keys
- Stripe webhook secrets
- Resend API keys
- Cloudflare tokens
- Render API keys
- Customer lead files
- Fulfillment exports

Any secret exposed in screenshots, chat, logs, or commits must be rotated immediately.

