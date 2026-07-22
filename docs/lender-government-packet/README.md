# NEXUS Lender And Government Packet

This packet collects the production evidence a lender, SBA reviewer, partner, or government buyer can review without needing direct access to secret values.

## Packet Index

- [Digital Asset Register](digital-asset-register.md)
- [Architecture Diagram](architecture-diagram.md)
- [Deployment Evidence](deployment-evidence.md)
- [Secret Management Proof](secret-management-proof.md)
- [Operations Runbook](../production-operations-runbook.md)
- [Rollback Plan](rollback-plan.md)

## Current Production Control Points

- Deployment control: ArgoCD GUI.
- Runtime: AKS namespace `nexus`.
- Images: Azure Container Registry `crjqmupr2v7hmzm`.
- Secrets: Azure Key Vault `nexusvault28095` through External Secrets Operator.
- TLS: cert-manager managed `nexuscloud-sh-tls`.
- Alerting: scheduled GitHub Actions production alert workflow.
- Evidence export: scheduled GitHub Actions evidence artifact workflow.
