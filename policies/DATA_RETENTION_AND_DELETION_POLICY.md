# Data Retention And Deletion Policy

Status: Draft  
Owner: Product owner and security owner  
Applies to: Lead data, enrichment data, scoring results, uploads, exports, logs, backups, billing records, and support records

## Purpose

Customer data should be retained only as long as needed for product operation, legal obligations, security, and customer commitments.

## Data Categories

| Data Type | Example | Default Retention | Notes |
| --- | --- | --- | --- |
| Customer account data | User profile, tenant settings | Active account plus agreed post-cancellation window | TBD |
| Lead data | Imported prospects and metadata | Customer-controlled | TBD |
| OSINT enrichment | Source-derived lead attributes | Customer-controlled with provenance | TBD |
| AI enrichment | Generated summaries, classifications, scores | Customer-controlled | TBD |
| Upload files | CSV/XLSX imports | Delete after processing or defined short retention | TBD |
| Exports/reports | Downloaded lead lists | Customer-controlled or short retention | TBD |
| Application logs | Operational events | TBD | Avoid sensitive data |
| Audit logs | Security and admin events | TBD | Longer retention may be required |
| Backups | Database/object backups | TBD | Restore-tested |
| Billing records | Subscription and invoice metadata | Legal/accounting retention | TBD |

## Requirements

- Customers must be able to request deletion or account closure.
- Deletion behavior must be documented clearly.
- Backups must have defined retention and eventual deletion behavior.
- Data retention must align with privacy policy and customer agreements.
- OSINT and AI-derived data must be traceable enough for review and correction.

## Launch Blockers

- No defined deletion process for customer data.
- Undefined backup retention.
- Uploads or exports retained indefinitely without reason.
- Privacy policy contradicts actual system behavior.

## Required Evidence

- Data inventory.
- Retention schedule.
- Deletion request workflow.
- Backup retention configuration.
- Sample deletion test result.

