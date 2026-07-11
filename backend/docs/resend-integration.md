# Resend Integration Guide

## Canonical configuration

- `RESEND_API_KEY`
- `RESEND_FROM`
- `EMAIL_DOMAIN`
- `WAITLIST_NOTIFY_TO`

## Setup

1. Create a Resend account and generate a server-side API key.
2. Add a dedicated sending subdomain such as `mail.example.com`.
3. Publish the DKIM/SPF DNS records that Resend provides.
4. Wait for domain verification before switching production traffic.
5. Set `RESEND_FROM` to a verified sender identity on that domain.

## Runtime behavior

- Email sending runs server-side only.
- Delivery retries use bounded exponential backoff on transient failures.
- Failure logging must never include the API key.
- Email failure must not block the core checkout or lead capture flow; it should log and continue with manual follow-up when necessary.

## Verification

- Submit a waitlist/demo flow and confirm the ops inbox receives the message.
- Trigger a Stripe test webhook and confirm buyer + ops notifications are sent.
- Review Render logs to confirm only sanitized error information is emitted.
