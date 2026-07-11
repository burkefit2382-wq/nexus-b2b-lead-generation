# Access Control Policy

Status: Draft  
Owner: Security owner  
Applies to: LeadGen Virtual Hub application, APIs, admin tools, support tooling, data stores, logs, and cloud accounts

## Purpose

Access is granted only to people and systems that need it for a legitimate business purpose. Permissions must be role-based, auditable, and removable when no longer needed.

## Roles To Define Before Launch

| Role | Intended Access | Launch Status |
| --- | --- | --- |
| Owner | Tenant settings, billing, user management, all tenant data | TBD |
| Admin | User management and operational configuration | TBD |
| Analyst | Lead import, enrichment, scoring, review, export | TBD |
| Standard user | Assigned lead workflows and dashboard access | TBD |
| Read-only user | View approved records and reports only | TBD |
| Support/admin operator | Limited support actions with audit trail | TBD |

## Requirements

- Every user must authenticate before accessing non-public resources.
- Every user action must be authorized by role and tenant.
- Tenant isolation is mandatory; one customer must not access another customer's data.
- Administrative access must be limited to named users and reviewed regularly.
- Privileged production access must use MFA where supported.
- Service accounts must have scoped permissions and documented owners.
- API keys and tokens must be scoped, revocable, rotated, and audited.
- Disabled users must lose access immediately.
- Support access to customer data must be logged and limited to approved support needs.

## Launch Blockers

- Any known auth bypass.
- Any cross-tenant data exposure.
- Any role able to perform actions outside its approved permission set.
- Shared production admin credentials.
- Missing or untested API authorization checks.

## Required Evidence

- RBAC matrix.
- Auth and role test results.
- API key lifecycle test results.
- Admin user list.
- Sample audit log entries for login, user invite, role change, export, and API key actions.

