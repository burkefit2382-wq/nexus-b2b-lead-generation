# Secret Management Proof

NEXUS production secrets are managed through Azure Key Vault and synced into Kubernetes by External Secrets Operator.

## Evidence Without Exposing Values

Acceptable evidence:

- Key Vault secret-name inventory.
- `ClusterSecretStore/nexus-azure-keyvault` status `Valid`.
- `ExternalSecret/nexus-secrets` status `SecretSynced`.
- Kubernetes `Secret/nexus-secrets` key count.
- ArgoCD `nexus-platform` sync and health status.

Unacceptable evidence:

- Raw Kubernetes Secret data.
- Decoded secret values.
- Key Vault secret values.
- Screenshots showing provider tokens or webhook secrets.

## Production Secret Names

```text
nexus-prod-DATABASE-URL
nexus-prod-HUBSPOT-ACCESS-TOKEN
nexus-prod-HUBSPOT-PORTAL-ID
nexus-prod-JWT-SECRET
nexus-prod-PRICE-ID
nexus-prod-RESEND-API-KEY
nexus-prod-RESEND-FROM
nexus-prod-STRIPE-SECRET-KEY
nexus-prod-STRIPE-WEBHOOK-SECRET
nexus-prod-WAITLIST-NOTIFY-TO
```
