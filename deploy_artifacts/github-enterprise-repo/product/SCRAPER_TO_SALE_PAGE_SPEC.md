# Scraper Output To AI-Enriched Lead Sale Page Spec

Status: Draft  
Owner: Product owner  
Applies to: 24/7 scraper output, AI enrichment, lead scoring, storefront-safe sale listings, and buyer requests

## Goal

Scraper output should become an AI-enriched lead package that can be listed for sale on the storefront page.

## Flow

1. Scraper captures a record from an approved source.
2. Nexus validates and deduplicates the record.
3. AI enrichment creates a summary and qualification context.
4. Lead scoring assigns score, band, confidence, and reasons.
5. Storefront-safe fields are generated.
6. A lead package appears on the sale page.
7. Buyer requests the lead package through a controlled workflow.

## Storefront Safety

- Public listing can show company, market, summary, score band, confidence, price, and included deliverables.
- Public listing must not show raw private phone/email, internal notes, sensitive identifiers, or unreviewed personal data.
- Buyer access to private details requires approval, terms, and applicable privacy/compliance checks.

## Current Local Demo

The Command Center includes:

- `For Sale` top-menu item.
- Default visible demo listing for `Northstar Labs`.
- `Generate enriched lead listing` button.
- `POST /api/sale-listing` endpoint.

