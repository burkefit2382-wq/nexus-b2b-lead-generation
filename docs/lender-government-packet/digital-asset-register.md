# Digital Asset Register

| Asset | Purpose | System Of Record | Evidence Source |
| --- | --- | --- | --- |
| `nexuscloud.sh` | Production SaaS domain | Cloudflare DNS | DNS record and HTTPS health export |
| AKS `nexus-aks` | Production Kubernetes runtime | Azure | AKS workload evidence export |
| Namespace `nexus` | Application runtime boundary | Kubernetes/ArgoCD | ArgoCD app `nexus-k8s` |
| ACR `crjqmupr2v7hmzm` | API and worker image registry | Azure Container Registry | ACR tag/digest export |
| ArgoCD `nexus-k8s` | NEXUS app deployment | ArgoCD | ArgoCD application export |
| ArgoCD `nexus-platform` | TLS, Key Vault, and policy config | ArgoCD | ArgoCD application export |
| Key Vault `nexusvault28095` | Production secret source | Azure Key Vault | Secret-name inventory export |
| cert-manager | TLS certificate automation | ArgoCD Helm app | Certificate status export |
| External Secrets Operator | Key Vault to Kubernetes sync | ArgoCD Helm app | ExternalSecret status export |
| GitHub Actions | Image builds, alerts, evidence exports | GitHub | Workflow run history |
