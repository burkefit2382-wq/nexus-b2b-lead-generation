# NEXUS OSINT Pipeline

The NEXUS worker collects public business and location records from OpenStreetMap Overpass and processes them through deterministic safety and quality gates before they can reach customer packages or CRM systems.

## Pipeline stages

1. **Collect** — Query allowlisted public OpenStreetMap data for configured Florida counties and business categories.
2. **Normalize** — Canonicalize business names, websites, phones, locations, timestamps, and retention metadata. Records past their configured retention window are removed from active outputs.
3. **Deduplicate** — Merge records by public business domain, public phone, or normalized name and location while preserving every source identifier.
4. **Compliance gate** — Quarantine non-allowlisted sources, unsupported subject types, prohibited personal-data fields, and records matching the suppression list.
5. **Score and route** — Preserve the existing OSINT quality score and route records to approved, manual-review, or quarantine outputs.
6. **Export** — Optionally export approved business records to HubSpot. Export is disabled by default and uses a durable export ledger to prevent repeated sends.
7. **Audit and observe** — Emit a run manifest, append-only audit events, Prometheus counters, and separate buyer-safe output queues.

## Outputs

The worker stores files beneath `backend/data/scrapers` locally and `/app/data/scrapers` in the worker container:

- `approved_leads.jsonl` — records eligible for packaging or explicitly enabled CRM export
- `manual_review_queue.jsonl` — records requiring analyst review
- `compliance_quarantine.jsonl` — blocked records and reason codes
- `pipeline_manifest.json` — counts, timings, retention, and export status for the latest run
- `pipeline_audit.jsonl` — append-only pipeline completion events
- `hubspot_export_state.json` — lead IDs already exported to HubSpot
- `suppression_list.jsonl` — operator-maintained opt-out identifiers

Kubernetes persists these files on the `nexus-osint-data` PVC.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `NEXUS_SCRAPER_COUNTIES` | Four Tampa Bay counties | Collection geography |
| `NEXUS_SCRAPER_TARGETS` | Configured business categories | Collection categories |
| `NEXUS_OSINT_RETENTION_DAYS` | `365` | Adds a retention-expiry timestamp to every record |
| `NEXUS_OSINT_SUPPRESSION_FILE` | `data/scrapers/suppression_list.jsonl` | Alternate suppression-list path |
| `NEXUS_OSINT_HUBSPOT_EXPORT` | `false` | Enables export of approved records only |

If HubSpot export is enabled, supply one supported HubSpot token through the existing Kubernetes secret mechanism. Never place the token in the manifest or repository.

## Suppression entries

Add one JSON object per line using a lead ID, canonical ID, normalized phone, or normalized website:

```json
{"value":"tb-example-lead-id","reason":"customer opt-out"}
```

The next pipeline run routes matching records to `compliance_quarantine.jsonl` with the `suppression_match` reason.

## Safe rollout

1. Deploy with `NEXUS_OSINT_HUBSPOT_EXPORT=false`.
2. Review `pipeline_manifest.json`, the manual-review queue, and quarantine reason codes.
3. Confirm the PVC is bound and survives a worker restart.
4. Configure the HubSpot token from Key Vault only if automatic export is desired.
5. Enable export after the review policy and opt-out process are operational.
