# Pricing And Billing Readiness

Status: Draft  
Owner: Business owner  
Applies to: SaaS packaging, pricing, subscriptions, billing operations, cancellation, refunds, and customer communication

## Purpose

Launch pricing and billing only when the customer promise, product limits, payment flow, support process, and cancellation path are clear.

## Packaging Decisions

| Decision | Options | Current Decision |
| --- | --- | --- |
| Launch type | Free pilot / paid pilot / private beta / public paid launch | TBD |
| Pricing model | Per seat / per tenant / usage-based / hybrid | TBD |
| Billing cadence | Monthly / annual / pilot contract | TBD |
| Trial | None / time-limited / usage-limited | TBD |
| Usage limits | Leads imported, enrichments, API calls, users, exports | TBD |
| Overage policy | Block / throttle / charge / manual approval | TBD |
| Government sales | Pilot agreement / purchase order / invoice | TBD |

## Suggested Initial Packages

These are placeholders for decision-making, not final prices.

| Package | Intended Buyer | Includes | Open Questions |
| --- | --- | --- | --- |
| Pilot | Trusted early customers | Limited users, sample datasets, guided onboarding, feedback loop | Is it free or paid? How long? |
| Team | Small commercial team | Core ingestion, enrichment, scoring, dashboard, exports | Seat and usage limits |
| Agency/Gov-Ready | Regulated or government-facing buyer | Audit logs, RBAC, API controls, security evidence packet, support SLA | Required compliance commitments |

## Billing Launch Blockers

- Pricing page or sales quote does not match actual product limits.
- Billing system can charge incorrectly.
- Customers cannot cancel or understand cancellation.
- Plan limits are not enforced or communicated.
- Billing events are not logged.
- Refund/credit process is undefined.
- Taxes, invoices, and payment terms are not decided for paid launch.

## Billing Smoke Tests

| Test | Expected Result | Evidence |
| --- | --- | --- |
| Create subscription | Customer is placed on correct plan | Screenshot/log |
| Upgrade plan | Access and invoice update correctly | Screenshot/log |
| Downgrade plan | Limits and next billing date are clear | Screenshot/log |
| Cancel subscription | Access follows cancellation policy | Screenshot/log |
| Failed payment | Customer is notified and access policy is enforced | Screenshot/log |
| Usage limit reached | Product blocks, throttles, or warns according to policy | Screenshot/log |
| Billing audit log | Plan changes and payment failures are captured | Redacted audit log |

## Required Before Paid Launch

- Pricing decision.
- Plan feature matrix.
- Payment provider selected and configured.
- Terms of service reviewed.
- Privacy policy reviewed.
- Refund/cancellation policy reviewed.
- Billing support workflow assigned.
- Test-mode billing evidence captured.

