# Onsite Tools And Storefront Automation Spec

Status: Draft  
Owner: Product owner  
Applies to: Onsite privacy sweep tools, consent-based location sharing, generated lead listings, and storefront publishing

## Purpose

Extend LeadGen Virtual Hub beyond lead generation into onsite operational tools and automated storefront publishing while protecting privacy, consent, and compliance.

## Feature 1: Onsite Room Privacy Sweep

Defensive use case: help an authorized user inspect a hotel room, office, rental unit, or meeting space for suspicious signals that may indicate hidden cameras, microphones, or wireless transmitters.

### Allowed Scope

- User-initiated checklist for visual inspection.
- RF/signal observation workflow using approved hardware or mobile-accessible sensors where available.
- Manual notes, photos, timestamps, and room checklist.
- Confidence levels such as `needs review`, `likely benign`, `suspicious`, or `escalate`.
- Safety guidance to contact hotel/security/law enforcement if a suspected surveillance device is found.

### Not Allowed

- Interfering with radio communications.
- Bypassing networks, passwords, or device security.
- Covertly scanning spaces where the user lacks authorization.
- Making guaranteed claims that no device exists.

### Launch Requirements

- Clear disclaimer: the sweep reduces risk but cannot guarantee detection.
- Hardware compatibility list.
- False-positive handling.
- Evidence export with timestamps.
- Privacy-safe storage controls for photos and room notes.

## Feature 2: Consent-Based Live Location Check-In

Requested unsafe version: live location from only a phone number.  
Safe product version: location sharing only after the person explicitly opens a secure link and grants location permission.

### Safe Flow

1. Authorized user sends a check-in request by SMS or email.
2. Recipient opens a secure link.
3. Recipient sees who is requesting location and why.
4. Recipient explicitly grants browser/device location permission.
5. System records the shared location, timestamp, consent event, and expiration.
6. Recipient can stop sharing or let the link expire.

### Required Controls

- Explicit consent screen.
- Expiring links.
- Audit log for request, consent, view, and expiration.
- No background tracking.
- No number-only tracking.
- No attempt to bypass carrier, device, app, or operating-system protections.
- Clear privacy disclosure.

## Feature 3: Generated Leads To Storefront Listings

Goal: leads generated in the platform can automatically become storefront listing drafts or published storefront cards.

### Recommended Workflow

1. Lead is imported or generated.
2. OSINT and AI enrichment run.
3. Lead score and publishing rules are evaluated.
4. A sanitized storefront listing draft is created.
5. Listing is reviewed manually or auto-published if it passes rules.
6. Storefront listing syncs status back to LeadGen Virtual Hub.

### Listing Fields

| Field | Source | Public By Default |
| --- | --- | --- |
| Listing title | Company/segment/name template | Yes |
| Category | Lead type or offer type | Yes |
| Region | City/state or service area | Yes, if not sensitive |
| Summary | AI-generated public-safe summary | Yes after review |
| Score band | High/medium/low or badge | Optional |
| Contact CTA | Platform-controlled form or internal routing | Yes |
| Raw phone/email | Lead source data | No |
| Notes | Internal sales notes | No |
| OSINT provenance | Source metadata | Internal by default |

### Publishing Modes

| Mode | Behavior | Best Use |
| --- | --- | --- |
| Draft only | Creates listing drafts for review | First pilot |
| Rule-approved | Auto-publishes only when rules pass | Controlled launch |
| Manual publish | User approves each listing | Regulated or sensitive workflows |
| API sync | Pushes approved listings to external storefront | Later integration |

### Storefront Safety Rules

- Do not publish personal phone numbers, private emails, home addresses, sensitive notes, or non-public identifiers.
- Do not publish AI claims that have not been reviewed or sourced.
- Do not publish leads marked private, restricted, government-sensitive, or do-not-contact.
- Keep audit records for draft creation, approval, publish, update, and unpublish.
- Allow quick unpublish.

### Launch Acceptance Criteria

- Lead-to-listing mapping is documented.
- At least one storefront destination is selected.
- Draft creation works from sample leads.
- Manual approval works.
- Auto-publish rules are configurable.
- Sensitive fields are excluded by default.
- Publish/unpublish events appear in audit logs.
- Storefront listing can link back to the original lead record for authorized users.

