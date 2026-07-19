# NEXUS Production Evidence Export

Generated: 2026-07-19 01:59:40Z

This folder intentionally stores inventory, status, and digest evidence only.
It does not export Kubernetes Secret values or Azure Key Vault secret values.

## Contents

- argocd-applications.txt: ArgoCD sync and health status.
- argocd-sync-status.png: image evidence generated from the live ArgoCD app table.
- aks-workloads.txt: NEXUS deployment, pod, ingress, certificate, and ExternalSecret status.
- https-health.txt: Public HTTPS health result.
- key-vault-secret-inventory.txt: Key Vault secret names only.
- acr-nexus-api-tags.json: API image tag/digest metadata.
- acr-nexus-worker-tags.json: worker image tag/digest metadata.
- certificate.yaml: cert-manager Certificate status.
- externalsecrets.yaml: ExternalSecret status.
- rollback-reference.md: release rollback reference.
