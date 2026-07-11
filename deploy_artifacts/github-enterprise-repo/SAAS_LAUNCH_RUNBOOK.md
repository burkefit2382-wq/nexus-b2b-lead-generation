# LeadGen Virtual Hub SaaS Launch Runbook

Use this runbook to move from staging validation to a controlled SaaS launch. It assumes the product handles lead ingestion, OSINT enrichment, AI enrichment, lead scoring, dashboard usage, APIs, authentication, and role-based access.

## Launch Principle

Do not launch on promises. Launch only when the current environment, test results, monitoring, rollback plan, and customer-facing workflows prove the product is ready.

## Launch Roles

| Role | Owner | Responsibility |
| --- | --- | --- |
| Launch owner | TBD | Final go/no-go decision and launch coordination |
| Product owner | TBD | Feature completeness, onboarding, demo mode, documentation |
| Engineering owner | TBD | Deployment, defects, rollback, service health |
| Security owner | TBD | Vulnerability triage, auth, keys, logs, compliance evidence |
| Support owner | TBD | Pilot feedback, launch support, customer issues |

## Required Environments

| Environment | Required Before Launch | Status |
| --- | --- | --- |
| Local development | Source code available, reproducible setup documented | Not available in this workspace |
| Staging | Production-like config, test data only, monitoring enabled | TBD |
| Production | Backups, monitoring, alerting, secrets, rollback path | TBD |

## Launch Gates

| Gate | Required Evidence | Status |
| --- | --- | --- |
| Functional QA | Completed `LAUNCH_QA_TEST_PLAN.md` with no critical failures | Not started |
| Security QA | Vulnerability, SAST, DAST, secret scan, auth/RBAC test evidence | Not started |
| Performance | 50, 100, and 200 user load results plus ingestion stress test | Not started |
| Reliability | Job retry, persistence, restart, and failure recovery test evidence | Not started |
| Compliance readiness | Policies, audit logs, RBAC matrix, encryption evidence, incident plan | In progress |
| UX/onboarding | Sign-up, onboarding, demo mode, docs, errors tested by pilot users | Not started |
| Pilot | 3 to 10 trusted testers complete real tasks and feedback is triaged | Not started |
| Support readiness | Help channel, response expectations, known issues, escalation path | Not started |
| Business readiness | Pricing, terms, privacy, billing, cancellation, refund process | Not started |

## Pre-Launch Checklist

- Confirm target customer profile and first launch audience.
- Confirm whether the launch is private beta, pilot, paid pilot, or public release.
- Confirm all user roles and permissions.
- Confirm production secrets are separate from staging secrets.
- Confirm API keys cannot be bypassed and can be rotated.
- Confirm audit logs capture auth, admin, ingestion, enrichment, scoring, export, and billing events.
- Confirm logs do not expose API keys, credentials, raw sensitive data, or model prompts containing confidential data.
- Confirm backups exist and a restore test has passed.
- Confirm monitoring covers uptime, API latency, error rate, job queue depth, failed jobs, database health, AI latency, and billing failures.
- Confirm alerts route to a named person.
- Confirm rollback can be executed within the agreed recovery window.

## Go/No-Go Meeting

Hold this meeting after final QA and before enabling production access.

| Question | Go Criteria |
| --- | --- |
| Are there any open critical or high defects? | No |
| Are auth, RBAC, API keys, and logs verified? | Yes |
| Did all critical user workflows pass? | Yes |
| Did load testing meet launch traffic targets? | Yes |
| Is monitoring active and staffed? | Yes |
| Is rollback tested or clearly executable? | Yes |
| Are privacy, terms, and data handling disclosures ready? | Yes |
| Are pilot findings triaged? | Yes |

Decision options:

- `Go`: launch as planned.
- `Go with watch`: launch to limited audience with named risks and active monitoring.
- `No-go`: delay launch until launch-blocking issues are fixed.

## Launch Day Sequence

1. Freeze non-critical changes.
2. Confirm staging and production versions.
3. Run smoke tests on staging.
4. Deploy to production.
5. Run production smoke tests:
   - Home/dashboard loads.
   - Login/logout works.
   - Role permissions hold.
   - API health endpoint responds.
   - Ingestion test job completes.
   - AI enrichment test completes.
   - Lead scoring returns expected result.
   - Billing flow works if enabled.
   - Logs and audit events appear.
6. Enable access for pilot or launch users.
7. Watch metrics for at least 2 hours:
   - API p95 latency.
   - Error rate.
   - Failed login spikes.
   - Failed ingestion jobs.
   - Queue depth.
   - Database CPU/connections.
   - AI model latency/errors.
   - Payment failures.
8. Record launch decision, version, and known issues.

## Rollback Criteria

Rollback if any of these occur and cannot be resolved quickly:

- Users cannot sign in.
- Users can access data or functions outside their role.
- API key bypass or auth bypass is suspected.
- Sensitive data appears in logs, browser output, exports, or support tools.
- Ingestion corrupts or duplicates customer data.
- AI enrichment or scoring writes destructive incorrect data.
- Dashboard or API error rate exceeds agreed threshold.
- Billing charges incorrectly.
- Production data backup or restore capability is unavailable.

## Post-Launch 72-Hour Watch

Review these at least daily for the first 72 hours:

- New user activation and onboarding completion.
- Support tickets and blocker themes.
- Failed jobs and retry counts.
- Enrichment accuracy complaints.
- Lead score consistency.
- API latency and error trends.
- Security alerts and suspicious activity.
- Billing and subscription failures.

## Launch Record Template

| Field | Value |
| --- | --- |
| Launch date | TBD |
| Launch type | Private beta / pilot / paid pilot / public |
| Version or commit | TBD |
| Environment URL | TBD |
| Launch owner | TBD |
| Go/no-go decision | TBD |
| Open accepted risks | TBD |
| Rollback owner | TBD |
| Monitoring owner | TBD |

