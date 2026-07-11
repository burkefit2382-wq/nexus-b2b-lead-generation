# Support Playbook

Status: Draft  
Owner: Support owner  
Applies to: Pilot and early launch customers

## Support Channels

| Channel | Purpose | Owner | Status |
| --- | --- | --- | --- |
| Email | Customer issues and feedback | TBD | TBD |
| Shared tracker | Defects and feature requests | TBD | `trackers/DEFECT_TRACKER.md` |
| Emergency contact | Security, data, billing, outage issues | TBD | TBD |

## Issue Categories

| Category | Examples | First Response |
| --- | --- | --- |
| Access | Login failure, invite missing, wrong role | Verify account, role, tenant, and recent auth logs |
| Ingestion | Upload failure, wrong row count, duplicate records | Capture file type, row count, error, job ID |
| OSINT | Missing/stale enrichment, source outage | Capture lead example, source, enrichment job ID |
| AI enrichment | Low-quality output, unexpected classification | Capture input fields, output, model/job ID |
| Scoring | Score seems wrong or inconsistent | Capture dataset, score factors, rerun result |
| Dashboard | Broken widget, slow page, browser console error | Capture URL, browser, screenshot, console logs |
| API | Auth failure, schema error, rate limit | Capture endpoint, request ID, status code |
| Billing | Wrong plan, failed payment, invoice issue | Capture billing event and plan state |
| Security/privacy | Data exposure, suspicious access, sensitive logs | Escalate immediately |

## Severity And Response

| Severity | Definition | Target |
| --- | --- | --- |
| Critical | Security, data exposure/loss, auth/RBAC bypass, billing error, total outage | Immediate escalation |
| High | Core workflow blocked or misleading results that harm trust | Same day |
| Medium | Important issue with workaround | 1 to 2 business days |
| Low | Cosmetic, copy, minor friction | Backlog |

## Escalation Rules

Escalate immediately when:

- Customer data may be exposed to the wrong user or tenant.
- A user can perform unauthorized actions.
- API keys or secrets appear in logs, UI, exports, or support tickets.
- Billing charges appear incorrect.
- Ingestion corrupts, deletes, or duplicates customer data.
- AI enrichment or scoring writes destructive incorrect output.
- Production service is unavailable.

## Support Response Template

```text
Thanks for reporting this. We are tracking it as [ID].

What we understand:
- Issue:
- Environment/account:
- Affected workflow:
- Current severity:

What we need, if available:
- Screenshot or screen recording:
- File name or job ID:
- Approximate time:
- Browser/API request details:

Next step:
- Owner:
- Expected update:
```

## Daily Pilot Review

During pilot, review every day:

- Open critical/high defects.
- Blocked testers.
- Repeated confusion points.
- Failed jobs.
- Slow or unreliable workflows.
- Trust concerns about enrichment/scoring.
- Security or privacy concerns.

