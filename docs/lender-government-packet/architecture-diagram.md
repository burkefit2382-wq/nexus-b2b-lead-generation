# Architecture Diagram

```mermaid
flowchart LR
  user["Customers / reviewers"] --> cf["Cloudflare DNS: nexuscloud.sh"]
  cf --> ingress["AKS ingress-nginx: 4.204.168.92"]
  ingress --> api["nexus-api deployment"]
  api --> kvsync["Kubernetes Secret: nexus-secrets"]
  worker["nexus-worker deployment"] --> kvsync
  kv["Azure Key Vault: nexusvault28095"] --> eso["External Secrets Operator"]
  eso --> kvsync
  git["GitHub main branch"] --> gha["GitHub Actions image build"]
  gha --> acr["Azure Container Registry"]
  gha --> gitops["GitOps image pin commit"]
  gitops --> argocd["ArgoCD GUI"]
  argocd --> api
  argocd --> worker
  argocd --> platform["cert-manager / External Secrets / policies"]
  platform --> cert["Let's Encrypt TLS certificate"]
  cert --> ingress
```

## Deployment Boundary

All production workload and platform changes flow through Git and ArgoCD. The emergency rollback procedure allows direct Kubernetes rollback only as a break-glass action, followed by a Git reconciliation.
