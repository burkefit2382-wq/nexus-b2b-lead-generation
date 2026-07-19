# Rollback Plan

## Preferred GitOps Rollback

1. Open ArgoCD.
2. Select `nexus-k8s`.
3. Identify the last healthy Git revision.
4. Revert the GitOps image pin commit or set the prior immutable image tag in `k8s/kustomization.yaml`.
5. Let ArgoCD sync or click `Sync`.
6. Confirm `nexus-api`, `nexus-worker`, HTTPS, and ExternalSecret checks pass.

## Emergency Rollback

```bash
kubectl -n nexus rollout undo deployment/nexus-api
kubectl -n nexus rollout undo deployment/nexus-worker
kubectl -n nexus rollout status deployment/nexus-api --timeout=180s
kubectl -n nexus rollout status deployment/nexus-worker --timeout=180s
```

After any emergency rollback, update Git immediately so ArgoCD does not reapply the bad release.

## Evidence To Capture

- Incident time.
- Bad Git revision and image tags.
- Rollback Git revision and image tags.
- ArgoCD sync status after rollback.
- `https://nexuscloud.sh/healthz` result.
- ExternalSecret and certificate status.
