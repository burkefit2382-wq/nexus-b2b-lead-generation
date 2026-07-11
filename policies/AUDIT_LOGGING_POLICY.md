# Audit Logging Policy

Status: Draft  
Owner: Security owner  
Applies to: Application, APIs, ingestion jobs, enrichment jobs, admin actions, exports, billing, and support actions

## Purpose

Audit logs must make important actions traceable without exposing secrets or sensitive raw data.

## Events To Log

- Login success and failure.
- Logout and session expiry.
- User invitation, creation, suspension, deletion, and role change.
- API key creation, use, rotation, revocation, and failed authentication.
- Lead import, enrichment job start/completion/failure, and lead scoring runs.
- Data export and report generation.
- Admin configuration changes.
- Billing plan changes, payment failures, and cancellation events if billing is enabled.
- Support/admin access to customer data.
- Security-relevant failures such as rate-limit blocks, suspicious requests, and permission denials.

## Log Content Requirements

Each audit event should include:

- Timestamp.
- Actor ID or service account.
- Tenant/customer ID.
- Event type.
- Target resource ID.
- Result: success, failure, denied, or partial.
- Source IP or request context where appropriate.
- Correlation/request ID.

## Prohibited Log Content

- Passwords.
- Full API keys or tokens.
- Payment card data.
- Raw secrets.
- Sensitive customer data unless explicitly required and protected.
- Full model prompts/responses containing confidential customer data unless approved by policy.

## Launch Blockers

- Sensitive secrets appear in logs.
- Admin and export actions are not auditable.
- Logs cannot identify actor, tenant, and action for critical workflows.

## Required Evidence

- Audit event catalog.
- Redacted sample logs.
- Log retention setting.
- Log access control list.
- Test showing secrets are redacted.

