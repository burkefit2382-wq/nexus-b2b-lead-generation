# NEXUS Government-Ready Launch Packet

This packet organizes the operating evidence a bank, SBA lender, government buyer, or partner reviewer will expect before trusting NEXUS as a production SaaS operation.

## Company And Product Summary

- Product: NEXUS B2B Lead Intelligence SaaS.
- Primary domain: `nexuscloud.sh`.
- Production platform: AKS, ArgoCD, Azure Container Registry, ingress-nginx.
- Revenue functions: lead packages, checkout, fulfillment notification, CRM integration.
- Operational model: GitOps-controlled Kubernetes deployment with auditable image tags and rollback.

## Digital Asset Register

| Asset | Purpose | Owner | System Of Record | Evidence |
| --- | --- | --- | --- | --- |
| `nexuscloud.sh` | Public production domain | Business owner | DNS registrar | DNS and ingress screenshot |
| GitHub repo | Source and GitOps history | Engineering owner | GitHub | Commit history and branch rules |
| ACR `crjqmupr2v7hmzm` | Container image registry | Engineering owner | Azure | Image tags and digests |
| AKS cluster | Production runtime | Engineering owner | Azure | Node, pod, ingress, and ArgoCD status |
| ArgoCD app `nexus-k8s` | Deployment control plane | Engineering owner | Kubernetes/ArgoCD | Sync and health screenshots |
| Azure Key Vault | Production secret source | Security owner | Azure | Secret inventory without values |
| Stripe account | Payment processing | Finance owner | Stripe | Product, price, and webhook config |
| HubSpot account | CRM/export workflow | Sales owner | HubSpot | Private app scopes and test export |
| Resend account | Fulfillment email | Operations owner | Resend | Sender and delivery status |

## SBA Bank Loan Packet

Core documents to keep in the lender folder:

- Business plan and executive summary.
- Use-of-funds schedule.
- 12-month cash flow forecast.
- Pricing and revenue model.
- Customer acquisition plan.
- Digital asset register.
- Production operations runbook.
- Security and secret-management process.
- Current deployment evidence.
- Insurance, licenses, contracts, and vendor agreements.
- Owner resume and business formation documents.

## Deployment Evidence Checklist

Capture these for each launch review:

- ArgoCD `nexus-k8s` is `Synced` and `Healthy`.
- `nexus-api` has desired available replicas.
- `nexus-worker` has desired available replicas.
- Public domain resolves to the ingress IP.
- `/healthz` and `/api/health` pass.
- TLS certificate is issued and valid.
- Latest image tags are immutable `sha-<commit>` tags.
- `nexus-secrets` is synced from Key Vault or the break-glass exception is documented.
- Rollback path has been tested or documented for the release.

## Risk Register

| Risk | Current Control | Next Control |
| --- | --- | --- |
| Secret exposure | Secret templates only in Git | External Secrets + Azure Key Vault |
| Image drift | ArgoCD GitOps app | CI image pin commits |
| TLS outage | Ingress prepared for cert-manager | cert-manager install and certificate alert |
| Worker failure | Worker deployment in `nexus` namespace | CronJob and log-based alerting |
| Failed release | Kubernetes rollout history | Git-first rollback procedure |
| Vendor dependency | Stripe, HubSpot, Resend documented | Vendor continuity notes and exports |

## Reviewer Notes

NEXUS should be presented as commercially operational, not as a certified federal system. For government contracting language, describe the current state as "government-ready operating evidence" until formal compliance assessments, written policies, and required certifications are complete.
