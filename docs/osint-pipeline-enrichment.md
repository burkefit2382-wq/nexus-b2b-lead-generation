# NEXUS OSINT Pipeline Enrichment

NEXUS collects buyer-safe public business and location records from OpenStreetMap Overpass for Tampa Bay target counties. The enrichment stage converts each raw public record into a reviewable lead package row without collecting private account data, hidden records, sensitive personal data, or credentialed-source content.

## Enrichment Outputs

Each record now includes:

- `data_completeness_score`: 0-100 score for public website, phone, structured address, coordinates, and public social tags.
- `fit_signals`: normalized sales signals such as owned business website, structured local address, county geofence verification, public phone, and package-ready OSINT QA.
- `buyer_persona`: buyer-facing segment such as real estate brokerage, mortgage partner, insurance agency, home-service contractor, cleaning operator, or life-sciences operator.
- `recommended_offer`: suggested NEXUS package or manual-review route.
- `outreach_angle`: storefront-safe positioning text for sales review.
- `enrichment_summary`: short buyer-ready summary of the public record.
- `compliance_notes`: explicit public-source collection boundary.
- `source_risk`: Low, Medium, or High source risk for review triage.

## Scheduled Scope

The Kubernetes CronJob `nexus-osint-scraper-quality` runs every six hours for:

- Pinellas
- Hillsborough
- Pasco
- Hernando

The scheduled target categories are:

- Real estate
- Mortgage and finance
- Insurance
- Home services
- Professional cleaning
- Biopharma and life sciences

## Review Rules

Records are approved for packaging only when the OSINT quality score is high and no review flags are present. Records with missing or inconsistent state, out-of-county coordinates, weak source completeness, or missing public contact context are routed to manual review.

## Safety Boundary

This pipeline is designed for defensive, commercial lead-intelligence use. It does not bypass authentication, scrape private systems, collect credentials, enrich private individuals, or expose raw lead files publicly.
