# Production Operations Runbook

This runbook covers NEXUS AKS deploys, health checks, alerting, TLS, rollback, and evidence capture for government-ready launch review.

## Deploy Path

1. Code merges to `main`.
2. GitHub Actions workflow `Build AKS images and update GitOps` builds `nexus-api` and `nexus-worker`.
3. Images are pushed to Azure Container Registry with immutable `sha-<commit>` tags.
4. The workflow updates `k8s/kustomization.yaml` with the new image tags and pushes the GitOps commit.
5. ArgoCD Application `nexus-k8s` syncs the `k8s` path into the `nexus` namespace.

Platform controllers are also registered in ArgoCD:

- `cert-manager`: installs and reconciles cert-manager through the Jetstack Helm chart.
- `external-secrets`: installs and reconciles External Secrets Operator through its Helm chart.
- `nexus-platform`: applies the NEXUS `ClusterIssuer`, Azure Key Vault `ClusterSecretStore`, and Key Vault smoke sync manifests.

## Health Checks

Kubernetes native checks:

- `nexus-api` readiness probe: `GET /healthz`.
- `nexus-api` liveness probe: `GET /healthz`.
- `nexus-internal-health` CronJob: runs every 5 minutes and verifies internal service health through `nexus-backend`.
- GitHub Actions uptime workflow: runs every 30 minutes against public routes.

Useful commands:

```bash
kubectl -n argocd get application nexus-k8s
kubectl -n nexus get deploy,svc,ingress,cronjob,pods
kubectl -n nexus get jobs --sort-by=.metadata.creationTimestamp
kubectl -n nexus logs deployment/nexus-api --tail=100
kubectl -n nexus logs deployment/nexus-worker --tail=100
```

## Alerting

Active alert policy:

- GitHub Actions workflow `NEXUS Production Alerts` runs every 15 minutes.
- The workflow fails when an ArgoCD app is not `Healthy`.
- The workflow fails when `nexus-api` or `nexus-worker` available replicas are below desired replicas.
- The workflow fails when `nexuscloud-sh-tls` is not Ready or expires within 14 days.
- The workflow fails when `nexus-secrets` or `nexus-keyvault-smoke` ExternalSecret sync is not Ready.
- The workflow fails when `https://nexuscloud.sh/healthz` does not return a healthy HTTP 200 response.

GitHub sends workflow failure notifications according to repository notification settings. For regulated or lender-facing operations, mirror these failures into Azure Monitor, email, or the business incident channel.

Azure Monitor command template:

```bash
az monitor metrics alert create \
  --name nexus-api-unavailable \
  --resource-group REPLACE_WITH_AKS_RESOURCE_GROUP \
  --scopes REPLACE_WITH_AKS_RESOURCE_ID \
  --condition "avg kube_deployment_status_replicas_available < 1" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action REPLACE_WITH_ACTION_GROUP_ID
```

Keep the GitHub Actions uptime workflow notifications enabled for repository admins, and connect Azure Monitor to email/SMS or the incident channel used by the business.

## Production Hardening

The `nexus-k8s` app applies:

- NetworkPolicies for default deny, API ingress, DNS egress, and approved external egress ports.
- PodDisruptionBudgets for API and worker.
- ResourceQuota and LimitRange for namespace resource controls.

The `nexus-platform` app applies:

- ValidatingAdmissionPolicy requiring NEXUS Deployments, Jobs, and CronJobs in the `nexus` namespace to use non-`latest` images from `crjqmupr2v7hmzm.azurecr.io`.
- External Secrets and cert-manager platform configuration.

AKS enforces Kubernetes NetworkPolicy with Calico. Confirm with:

```bash
az aks show --resource-group nexus-rg --name nexus-aks --query networkProfile.networkPolicy -o tsv
```

## HTTPS/TLS

The ingress is prepared for cert-manager with:

- host: `nexuscloud.sh`
- TLS secret: `nexuscloud-sh-tls`
- ClusterIssuer: `letsencrypt-production`

Install cert-manager before applying the ClusterIssuer template. Then apply:

```bash
kubectl apply -f k8s/certificates/clusterissuer-letsencrypt-production.template.yaml
kubectl -n nexus describe certificate nexuscloud-sh-tls
```

If the certificate does not issue, confirm `nexuscloud.sh` resolves to the ingress IP and that HTTP-01 challenge paths are not blocked.

## Rollback

Preferred rollback is Git-first:

1. Open ArgoCD GUI at `http://127.0.0.1:8080`.
2. Open `nexus-k8s`.
3. Review the current sync revision.
4. Revert the GitOps image pin commit or set the prior image tag in `k8s/kustomization.yaml`.
5. Let ArgoCD sync, or click `Sync`.

Emergency Kubernetes rollback:

```bash
kubectl -n nexus rollout undo deployment/nexus-api
kubectl -n nexus rollout undo deployment/nexus-worker
kubectl -n nexus rollout status deployment/nexus-api --timeout=180s
kubectl -n nexus rollout status deployment/nexus-worker --timeout=180s
```

After any emergency rollback, reconcile Git so ArgoCD does not roll the cluster forward again on the next sync.

## Evidence Log

For each production release, capture:

- Git commit and ArgoCD sync revision.
- Image tags and ACR digest.
- Rollout status for API and worker.
- Health check results.
- TLS certificate status.
- Secret rotation or confirmation date.
- Known risks and owner sign-off.

