# Incident Response Plan

Status: Draft  
Owner: Security owner  
Applies to: Security incidents, data exposure, availability incidents, auth failures, billing-impacting incidents, and abuse events

## Purpose

The team must be able to detect, triage, contain, investigate, communicate, recover from, and learn from incidents.

## Severity Levels

| Severity | Definition | Response Target |
| --- | --- | --- |
| SEV-1 | Confirmed or likely data breach, auth bypass, cross-tenant exposure, widespread outage, incorrect billing at scale | Immediate response |
| SEV-2 | Major degraded service, high-risk vulnerability, failed critical jobs, suspicious abuse pattern | Same day |
| SEV-3 | Limited customer impact or non-critical degradation | Next business day |
| SEV-4 | Minor issue, informational alert, low-risk finding | Planned triage |

## Response Process

1. Detect and record the incident.
2. Assign an incident lead.
3. Classify severity.
4. Preserve logs and evidence.
5. Contain the issue.
6. Eradicate root cause.
7. Recover service.
8. Communicate to affected parties when required.
9. Complete post-incident review.
10. Track corrective actions to closure.

## Incident Contacts

| Role | Name | Contact |
| --- | --- | --- |
| Incident lead | TBD | TBD |
| Engineering lead | TBD | TBD |
| Security lead | TBD | TBD |
| Customer/support lead | TBD | TBD |
| Legal/privacy contact | TBD | TBD |

## Launch Blockers

- No named incident owner.
- No way to receive production alerts.
- No access to logs needed for investigation.
- No customer communication path.

## Required Evidence

- Incident contact list.
- Alert routing configuration.
- Incident ticket/template.
- Sample post-incident review template.
- Log access and preservation process.

