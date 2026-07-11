# AI Scoring And Data Enrichment Spec

Status: Draft  
Owner: Product owner  
Applies to: Post-scrape enrichment, lead scoring, storefront draft creation, and explainable AI outputs

## Goal

After a scraper captures a lead record, Nexus should validate it, enrich it, score it, and prepare a storefront-safe draft.

## Pipeline

1. Scraper captures record from approved source.
2. Ingestion validates required fields.
3. Dedupe checks existing leads.
4. OSINT enrichment adds source-backed context.
5. AI enrichment summarizes the opportunity.
6. Lead scoring assigns score, band, confidence, and reasons.
7. Storefront-safe fields are generated.
8. Human review or auto-publish rules decide the next step.

## Output Fields

| Field | Purpose |
| --- | --- |
| `summary` | Plain-language lead context |
| `score` | Numeric score from 0 to 100 |
| `scoreBand` | High, medium, or low priority |
| `confidence` | Confidence level based on signal strength |
| `reasons` | Explainable scoring reasons |
| `nextAction` | Review, hold, outreach, or storefront draft |
| `storefrontSafeFields` | Public-safe listing fields |

## Guardrails

- Do not publish raw private contact data by default.
- Keep scoring reasons explainable.
- Track source provenance.
- Route low-confidence enrichment to review.
- Keep AI output as decision support, not guaranteed fact.
- Log enrichment and scoring runs.

## Current Local Demo

The Command Center includes:

- Visible `Enrichment` menu section.
- `Run AI pipeline` button.
- `POST /api/enrich-score` endpoint.
- Demo scoring response for a sample scraped lead.

