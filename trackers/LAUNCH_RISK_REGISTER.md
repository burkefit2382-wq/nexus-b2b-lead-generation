# Launch Risk Register

Use this register for accepted risks, open launch concerns, and explicit go/no-go decisions.

| ID | Risk | Area | Severity | Owner | Mitigation | Status | Launch Decision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-001 | Application source/build is not available in this workspace | Product readiness | Critical | TBD | Provide repo, exported build, or staging URL with test credentials | Open | No-go until resolved |
| R-002 | Functional, security, load, and reliability tests have not been executed | QA | Critical | TBD | Execute `LAUNCH_QA_TEST_PLAN.md` once app access exists | Open | No-go until resolved |
| R-003 | Compliance policies are drafts and not approved | Compliance | High | TBD | Review, customize, approve, and store signed versions in `evidence/01_policies` | Open | Limited pilot only |
| R-004 | Pricing, plan limits, billing provider, and cancellation/refund policy are undecided | Business readiness | High | TBD | Finalize `business/PRICING_AND_BILLING_READINESS.md` before paid launch | Open | No-go for paid launch |
| R-005 | Privacy policy and terms of service are not final legal documents | Legal/privacy | High | TBD | Complete `business/TERMS_PRIVACY_REVIEW_CHECKLIST.md` and obtain review | Open | No-go for public/paid launch |
| R-006 | Support owner, customer channel, and escalation contacts are not assigned | Support readiness | Medium | TBD | Finalize `customer/SUPPORT_PLAYBOOK.md` | Open | Blocks public launch; pilot can proceed only with named owner |
| R-007 | Launch site is only deployed locally, not to a public domain | Deployment | High | TBD | Choose hosting provider/domain and upload `deploy_artifacts/leadgen-virtual-hub-launch-site.zip` | Open | Blocks public launch |
| R-008 | Waitlist form has a local backend endpoint but no public persistent CRM/database/storefront destination | Lead capture | High | TBD | Connect `/api/waitlist` to CRM, database, or storefront backend in public hosting | Open | Blocks public launch |
| R-009 | Generated lead storefront publishing is specified but not implemented against a real storefront API | Storefront integration | High | TBD | Select storefront platform and build sanitized listing sync | Open | Blocks storefront automation launch |
| R-010 | Resend API key and sender domain are not configured in a backend environment | Email integration | High | TBD | Set `RESEND_API_KEY`, verify domain, and configure sender variables for `/api/waitlist` | Open | Blocks public waitlist notifications |

## Risk Decision Rules

- Critical risks block public launch.
- High risks block public launch unless formally accepted for a limited pilot.
- Any auth, tenant isolation, secrets, billing, or data loss risk blocks launch.
