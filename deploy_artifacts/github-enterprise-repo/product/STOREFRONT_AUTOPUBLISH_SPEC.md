# Storefront Auto-Publish Spec

Status: Draft  
Owner: Product owner  
Applies to: Generated leads, sanitized storefront listings, approval workflows, and storefront API sync

## Goal

Generated leads should automatically become storefront-ready listings without exposing private lead data.

## Safe Publishing Model

LeadGen Virtual Hub should create a listing draft from each qualified lead. Publishing can be manual or automatic based on rules.

## Lead To Listing Mapping

| Lead Field | Storefront Field | Publish By Default |
| --- | --- | --- |
| Company or lead name | Listing title | Yes |
| Lead category/type | Category | Yes |
| Region or market | Location/service area | Yes, if not sensitive |
| AI public summary | Description | Only after review or safe-rule pass |
| Score band | Badge/filter | Optional |
| Internal owner | Internal only | No |
| Phone/email | Private routing field | No |
| Raw notes | Internal only | No |
| OSINT source metadata | Internal provenance | No |

## Publishing Modes

- `draft_only`: create listing drafts for review.
- `manual_publish`: require user approval before publishing.
- `rule_approved`: auto-publish if safety and score rules pass.
- `api_sync`: sync approved listings to a selected storefront API.

## Required Controls

- Exclude personal contact details by default.
- Exclude private notes and sensitive identifiers.
- Prevent publishing restricted, do-not-contact, or government-sensitive records.
- Log draft, approve, publish, update, and unpublish actions.
- Provide quick unpublish.
- Keep a link from listing back to original lead for authorized users only.

## Launch Blockers

- No selected storefront platform/API.
- No field mapping.
- No approval workflow.
- No privacy filter for contact details and notes.
- No audit trail for publish/unpublish.

