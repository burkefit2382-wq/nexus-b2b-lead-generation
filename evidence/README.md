# Evidence Folder

Store launch and compliance evidence here. Evidence should be dated, tied to a specific environment/version, and easy for a reviewer to verify.

## Folder Map

| Folder | Use |
| --- | --- |
| `00_system-overview` | Product overview, scope, architecture summary, environment list |
| `01_policies` | Approved policies and policy review records |
| `02_architecture` | Diagrams, data flows, trust boundaries, tenant isolation design |
| `03_access-control` | RBAC matrix, auth tests, API key tests, user access reviews |
| `04_security-testing` | Dependency scans, SAST, DAST, secret scans, TLS/header checks |
| `05_performance-testing` | Load tests, AI latency benchmarks, ingestion stress results |
| `06_reliability-testing` | Restart/failover/retry/job persistence tests |
| `07_audit-logs` | Audit event catalog and redacted sample logs |
| `08_privacy-data-retention` | Data inventory, deletion tests, retention settings |
| `09_incident-response` | Contact list, tabletop notes, incident templates |
| `10_vendor-ai-osint` | Vendor list, AI provider settings, OSINT source inventory |

## Evidence Naming

Use this format:

```text
YYYY-MM-DD_environment_short-description_owner.ext
```

Example:

```text
2026-06-17_staging_secret-scan_security.html
```

## Evidence Minimums

Each evidence item should answer:

- What was tested or reviewed?
- Who ran or approved it?
- Which environment and version did it cover?
- When was it captured?
- What was the result?
- Where are any follow-up tickets?

