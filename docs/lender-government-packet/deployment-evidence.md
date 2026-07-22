# Deployment Evidence

Use the scheduled `NEXUS Production Evidence Export` workflow or run:

```powershell
./scripts/export-production-evidence.ps1
```

The evidence export includes:

- ArgoCD sync and health status.
- AKS deployment, pod, ingress, CronJob, PDB, quota, NetworkPolicy, certificate, and ExternalSecret status.
- HTTPS health check result.
- Key Vault secret-name inventory without values.
- ACR image tag and digest metadata.
- cert-manager Certificate status.
- External Secrets sync status.

Current expected production state:

- `nexus-k8s`: `Synced` and `Healthy`.
- `nexus-platform`: `Synced` and `Healthy`.
- `cert-manager`: `Synced` and `Healthy`.
- `external-secrets`: `Synced` and `Healthy`.
- `nexus-api`: two available replicas.
- `nexus-worker`: one available replica.
- `nexuscloud-sh-tls`: Ready.
- `nexus-secrets`: synced from Azure Key Vault.
