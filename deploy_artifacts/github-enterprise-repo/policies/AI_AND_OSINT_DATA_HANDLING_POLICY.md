# AI And OSINT Data Handling Policy

Status: Draft  
Owner: Product owner and security owner  
Applies to: AI enrichment, lead scoring, OSINT modules, prompts, model outputs, source data, exports, and audit records

## Purpose

AI and OSINT features must produce useful lead intelligence while protecting customer data, preserving provenance, and avoiding unsupported claims.

## AI Requirements

- Document model provider, model name, data retention settings, and whether customer data is used for training.
- Avoid sending secrets, API keys, or unnecessary sensitive fields to AI providers.
- Keep prompts and outputs out of logs unless redacted and approved.
- Provide reviewable outputs for lead enrichment and scoring.
- Make lead scoring consistent for fixed inputs or document expected variance.
- Avoid using AI output as an irreversible destructive action.
- Track model latency, errors, and fallback behavior.

## OSINT Requirements

- Document each OSINT source.
- Confirm source usage is lawful and permitted by source terms.
- Track provenance for enriched fields where practical.
- Handle rate limits and source outages gracefully.
- Avoid misrepresenting uncertain or stale external data as verified fact.

## Launch Blockers

- Unknown AI data retention/training behavior.
- Prompts or model outputs leak sensitive customer data into logs.
- OSINT source use is undocumented.
- Lead scoring is inconsistent without explanation.
- AI output overwrites customer data without review or rollback.

## Required Evidence

- Model/provider configuration.
- AI data flow diagram.
- OSINT source inventory.
- Sample enrichment outputs.
- Lead scoring consistency test.
- Log redaction test for prompts and outputs.

