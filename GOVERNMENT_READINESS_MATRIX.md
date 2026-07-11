# Government-Facing SaaS Security And Compliance Readiness Matrix

This matrix helps prepare LeadGen Virtual Hub for government-oriented buyers. It is not a FedRAMP, CMMC, FISMA, SOC 2, or ISO certification by itself. It is an evidence map for becoming credible, audit-ready, and procurement-ready.

## Official Reference Anchors

- NIST Cybersecurity Framework 2.0: https://www.nist.gov/cyberframework
- NIST SP 800-53 Rev. 5 security and privacy controls: https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final
- NIST SP 800-218 SSDF secure software development framework: https://csrc.nist.gov/pubs/sp/800/218/final
- FedRAMP Rev. 5 documents and templates: https://www.fedramp.gov/rev5/documents-templates/
- FedRAMP Rev. 5 agency authorization resources: https://www.fedramp.gov/rev5/agency-authorization/
- CISA Secure by Design: https://www.cisa.gov/securebydesign
- DCSA CMMC overview for DoD-facing contractor expectations: https://www.dcsa.mil/Industrial-Security/Controlled-Unclassified-Information-CUI/Cybersecurity-Maturity-Model-Certification-CMMC/

## Control Evidence Matrix

| Domain | Required Evidence | Product/Operational Requirement | Status |
| --- | --- | --- | --- |
| Asset inventory | System boundary, service list, data stores, third-party services | Document what is in scope for the SaaS | Missing |
| Data classification | Data types, sensitive fields, CUI/FCI determination if DoD-facing | Label lead data, enrichment data, logs, exports, prompts | Missing |
| Access control | RBAC matrix, admin approval process, least privilege review | Users only access authorized tenants, roles, APIs, exports | Missing |
| Authentication | MFA support, password/session policy, SSO plan if enterprise | Secure login, session expiry, lockout/rate limits | Missing |
| API security | API key lifecycle, auth tests, rate limits, scoped tokens | Keys can be rotated, revoked, audited, and cannot bypass RBAC | Missing |
| Tenant isolation | Tenant boundary design and tests | One customer's data cannot be read or inferred by another | Missing |
| Audit logging | Audit event catalog and sample export | Log auth, admin, data changes, jobs, exports, billing, API key actions | Missing |
| Log protection | Redaction policy and log access controls | Logs do not expose credentials, API keys, sensitive raw data, or prompt data | Missing |
| Encryption in transit | TLS scan and configuration evidence | HTTPS everywhere, no mixed content, secure cookies | Missing |
| Encryption at rest | Database, object storage, backups, queue, and log encryption proof | Sensitive data encrypted with managed keys or documented controls | Missing |
| Secrets management | Secret store config, rotation procedure, secret scan report | No hardcoded secrets in repo, bundles, logs, or artifacts | Missing |
| Secure SDLC | SAST, dependency scan, code review, release checklist | Security checks run before release | Missing |
| Vulnerability management | Scan reports, triage SLA, remediation tickets | Critical/high issues fixed before launch or formally accepted | Missing |
| Incident response | Incident response plan, severity levels, contact list | Team can detect, contain, investigate, notify, and recover | Missing |
| Backup/recovery | Backup policy, restore test, RPO/RTO | Customer data can be restored within target windows | Missing |
| Availability | Monitoring, alerting, uptime target, failover/retry evidence | Jobs and user workflows recover from service failures | Missing |
| Privacy | Privacy policy, data processing terms, deletion process | Customer data handling is disclosed and enforceable | Missing |
| Data retention | Retention schedule and deletion evidence | Leads, logs, job outputs, exports, and backups have defined lifetimes | Missing |
| AI governance | Prompt/data handling, model provider terms, output review policy | AI enrichment does not leak data or create unreviewed high-risk decisions | Missing |
| OSINT governance | Source list, allowed-use policy, provenance tracking | OSINT data sources are lawful, documented, and explainable | Missing |
| Compliance package | Policies, diagrams, scan reports, test evidence, risk register | Buyer can review readiness without ad hoc scrambling | Missing |

## Minimum Policies To Draft Before Government Sales

- Access Control Policy
- Acceptable Use Policy
- Audit Logging Policy
- Backup And Recovery Policy
- Change Management Policy
- Data Classification Policy
- Data Retention And Deletion Policy
- Encryption And Key Management Policy
- Incident Response Plan
- Privacy Policy
- Secure Development Policy
- Vulnerability Management Policy
- Vendor And Subprocessor Policy
- AI Data Handling Policy
- OSINT Data Source And Usage Policy

## Procurement-Ready Evidence Packet

Create a folder named `evidence/` when test artifacts are available. Store dated evidence using this shape:

```text
evidence/
  00_system-overview/
  01_policies/
  02_architecture/
  03_access-control/
  04_security-testing/
  05_performance-testing/
  06_reliability-testing/
  07_audit-logs/
  08_privacy-data-retention/
  09_incident-response/
  10_vendor-ai-osint/
```

## Security Test Commands To Run When Source Is Available

Use the tools that match the stack. Record exact versions and outputs.

```powershell
# JavaScript/TypeScript dependency scan
npm audit --audit-level=high

# Python dependency scan, if Python is used
pip-audit

# Secret scan, if gitleaks is installed
gitleaks detect --source . --redact

# Container scan, if images are used
trivy image <image-name>

# OWASP ZAP baseline, only against an authorized staging target
zap-baseline.py -t https://staging.example.com -r zap-report.html
```

## Launch Security Minimums

These are blockers for any production launch:

- No known auth bypass.
- No cross-tenant data access.
- No exposed production API keys or secrets.
- No unresolved critical/high vulnerabilities without documented executive risk acceptance.
- No sensitive data in logs.
- HTTPS enforced.
- Backups enabled and restore tested.
- Admin actions audited.
- API rate limiting enabled.
- Incident response contact and escalation path defined.

