# 10 Launch Checklist

## Final 48-72 Hour Launch Plan

## 1. Confirm Production Status

- [ ] `https://nexuscloud.sh/` returns 200.
- [ ] `https://nexuscloud.sh/dashboard` returns 200.
- [ ] `https://nexuscloud.sh/api/revenue-status` returns 200.
- [ ] `https://nexuscloud.sh/api/fulfillment-status` returns 200.
- [ ] Render deploy is live.
- [ ] Cloudflare route is stable.

## 2. Confirm Payments

- [ ] Stripe live key is set in Render.
- [ ] Stripe webhook secret is set in Render.
- [ ] Webhook endpoint is `https://nexuscloud.sh/api/stripe-webhook`.
- [ ] Test checkout succeeds.
- [ ] Fulfillment event appears in dashboard.
- [ ] No raw secrets are visible in logs or frontend code.

## 3. Confirm Email Fulfillment

- [ ] Resend domain is verified.
- [ ] `RESEND_FROM` uses verified domain.
- [ ] `WAITLIST_NOTIFY_TO` or `RESEND_TO` is set.
- [ ] Buyer confirmation email sends.
- [ ] Admin notification email sends.
- [ ] Failed delivery has manual fallback.

## 4. Confirm CRM

- [ ] HubSpot private app/service key is valid.
- [ ] `/api/hubspot-status` reports configured.
- [ ] Test contact export succeeds.
- [ ] Contact appears in HubSpot.
- [ ] Follow-up task/workflow exists.

## 5. Confirm Storefront Offers

Current lead packages:

| Offer | Price |
| --- | ---: |
| Tampa Bay 10-Lead Sprint | $350 |
| Tampa Bay 25-Lead Growth Sprint | $700 |
| Tampa Bay 50-Lead Domination Sprint | $1,000 |

Recurring offers to publish:

| Offer | Price Range |
| --- | ---: |
| Lead Drops Subscription | $99-$499/mo |
| Territory Exclusivity Subscription | $499-$1,500/mo |
| OSINT Monitoring Subscription | $49-$199/mo |
| Business Intelligence Subscription | $99-$299/mo |
| API Access | $500-$1,500/mo |
| White-label Agency Leadgen | $1,000-$5,000/mo |

## 6. Confirm Security Gates

- [ ] No real secrets in Git.
- [ ] GitHub secret scanning enabled.
- [ ] Dependabot enabled.
- [ ] Cloudflare WAF/rate limiting configured.
- [ ] Admin surfaces are protected or not publicly exposed.
- [ ] Stripe webhook signature verification tested.
- [ ] API rate limits planned for chat/enrichment/report endpoints.

## 7. Confirm Data Quality

- [ ] Remove out-of-scope New Hampshire records from Tampa Bay packs.
- [ ] Prioritize score-100/high-quality records.
- [ ] Enrich missing contact fields where lawful.
- [ ] Segment real estate vs mortgage vs home services.
- [ ] Do not publicly expose raw personal data.
- [ ] Include data quality caveats in pilot packs.

## 8. Confirm Documentation

- [ ] Enterprise docs published.
- [ ] Buyer transfer package ready.
- [ ] API docs reviewed.
- [ ] Deployment docs reviewed.
- [ ] CRM docs reviewed.
- [ ] Security docs reviewed.
- [ ] SLA docs reviewed.

## 9. Go-To-Market Action

Today:

- [ ] Post lead offer on Facebook.
- [ ] DM 20 local real estate agents or brokers.
- [ ] Send 5 professional sample/pilot emails.
- [ ] Offer one clear product: Tampa Bay 10-Lead Sprint for $350.
- [ ] Track source, campaign, date sent, reply, booked call, qualified, closed, revenue.

## Launch Decision

Launch when:

- Public site is stable.
- Checkout works.
- Resend works.
- Fulfillment dashboard records events.
- CRM export is tested or manual CRM fallback is documented.
- Lead package quality is reviewed by a human before delivery.
