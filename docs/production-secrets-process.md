# Production Secrets Process

NEXUS production secrets should live in Azure Key Vault, then sync into Kubernetes as the `nexus/nexus-secrets` Secret through External Secrets Operator. Do not commit raw `Secret` manifests with live values.

## Target State

- System of record: Azure Key Vault.
- Kubernetes delivery: External Secrets Operator.
- Runtime secret name: `nexus-secrets`.
- Git content: only templates and non-secret references.
- Rotation: update Key Vault first; External Secrets reconciles the Kubernetes Secret.

Current activation state:

- External Secrets Operator is managed by ArgoCD Application `external-secrets`.
- `nexus-platform` owns the Azure Key Vault `ClusterSecretStore`.
- `nexus-keyvault-smoke` proves Key Vault sync against `nexusvault28095` without overwriting the live production `nexus-secrets` Secret.
- `nexus-secrets` is managed by External Secrets with `creationPolicy: Merge`, using the full `nexus-prod-*` production secret set from Key Vault.

## Required One-Time Setup

1. Install External Secrets Operator into the cluster.
2. Enable AKS workload identity or provide an approved managed identity path.
3. Grant the External Secrets identity read access to the NEXUS Key Vault secrets.
4. Copy `k8s/secrets/external-secrets/azure-key-vault-store.template.yaml`, replace the tenant and vault placeholders, then apply it.
5. Copy `k8s/secrets/external-secrets/nexus-external-secret.template.yaml`, confirm the remote secret names, then apply it.
6. Confirm Kubernetes has the synced secret:

```bash
kubectl -n nexus get externalsecret nexus-secrets
kubectl -n nexus get secret nexus-secrets
```

## Key Vault Secret Names

Use these names unless a bank, auditor, or government buyer requires a different naming standard:

```text
nexus-prod-STRIPE-SECRET-KEY
nexus-prod-STRIPE-WEBHOOK-SECRET
nexus-prod-PRICE-ID
nexus-prod-DATABASE-URL
nexus-prod-RESEND-API-KEY
nexus-prod-RESEND-FROM
nexus-prod-WAITLIST-NOTIFY-TO
nexus-prod-HUBSPOT-ACCESS-TOKEN
nexus-prod-HUBSPOT-PORTAL-ID
```

## Rotation Runbook

1. Create the replacement value in the upstream provider.
2. Update the Azure Key Vault secret value.
3. Wait for External Secrets to refresh or force refresh with an annotation.
4. Restart affected deployments only if the application does not reload environment variables:

```bash
kubectl -n nexus rollout restart deployment nexus-api
kubectl -n nexus rollout status deployment nexus-api --timeout=180s
```

5. Record the rotation date, operator, affected secret names, and validation result in the launch evidence log.

## Break-Glass

If External Secrets is down during an incident, a short-lived manual Secret can be applied from an operator workstation. Delete it after the controller is restored and verify Key Vault is the source of truth again.
