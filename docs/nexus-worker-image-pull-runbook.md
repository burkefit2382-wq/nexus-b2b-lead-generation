# NEXUS Worker Image Pull Recovery Runbook

Status: cluster healthy; stale `default/nexus-worker` was failing image pull.

## Actual Finding From The Live Cluster

The failing worker was not in the `nexus` namespace:

```text
namespace: default
deployment: nexus-worker
image: your-acr.azurecr.io/nexus-worker:latest
status before fix: ErrImagePull / ImagePullBackOff
```

That image is a placeholder, and Azure Container Registry currently lists only:

```text
nexus-api
```

No `nexus-worker` repository exists in `crjqmupr2v7hmzm.azurecr.io`, and the deployment has no owner references or GitOps management labels. The reversible cleanup is:

```powershell
kubectl -n default scale deployment nexus-worker --replicas=0
```

Verified after cleanup:

```text
default/nexus-worker: 0/0
nexus/nexus-api: 2/2 Running
nexus/nexus-osint-scraper-quality jobs: Completed
```

## Successful Real Worker Deployment

On 2026-07-18, a real worker image was built in ACR using Azure remote build because local Docker was not installed:

```powershell
az acr build --registry crjqmupr2v7hmzm --image nexus-worker:latest --file backend\Dockerfile.worker backend
```

Built image:

```text
crjqmupr2v7hmzm.azurecr.io/nexus-worker:latest
digest: sha256:230f7e206dc4b73b7817f3c77feef0261b9aa91de5b5ba5f84df17483576e137
```

Deployed intentionally into the `nexus` namespace:

```powershell
kubectl apply -f deploy_artifacts\render-repo-work\k8s\deployments\nexus-worker-deployment.yaml
kubectl -n nexus rollout status deployment nexus-worker --timeout=240s
```

Verified:

```text
nexus/nexus-worker: 1/1 Running
image: crjqmupr2v7hmzm.azurecr.io/nexus-worker:latest
default/nexus-worker: 0/0 scaled down placeholder deployment
```

## What This Means

If ArgoCD, Argo Workflows, Ingress NGINX, Nexus API, OSINT jobs, metrics server, CSI drivers, and the nodepool are healthy, the issue is isolated to the worker pod image reference or registry authentication.

The pod spec must include the correct pull secret:

```yaml
imagePullSecrets:
  - name: dockerhub-secret
```

The Helm chart now supports `.Values.imagePullSecrets`, and the ArgoCD application values include `dockerhub-secret`.

## Confirm The Real Failure

```powershell
kubectl get pods -A
kubectl get deploy,sts,ds,job,cronjob -A
kubectl get events -A --sort-by=.lastTimestamp
```

Look for one of these:

- `ErrImagePull`
- `ImagePullBackOff`
- `pull access denied`
- `unauthorized: authentication required`
- `manifest unknown`
- `no basic auth credentials`

## Confirm The Worker Image

```powershell
kubectl -n default get deployment nexus-worker -o jsonpath="{.spec.template.spec.containers[*].image}"
```

If the image starts with Docker Hub, for example:

```text
docker.io/<org>/<image>:<tag>
<org>/<image>:<tag>
```

then `dockerhub-secret` is correct.

If the image starts with Azure Container Registry, for example:

```text
crjqmupr2v7hmzm.azurecr.io/nexus-worker:latest
```

then `dockerhub-secret` is the wrong secret unless it happens to contain ACR credentials. Create/use an ACR-specific secret instead.

## Create Or Refresh Docker Hub Secret

Run this in the same namespace as the failing worker. For the stale deployment found on 2026-07-18, that namespace was `default`, not `nexus`:

```powershell
kubectl -n default delete secret dockerhub-secret --ignore-not-found
kubectl -n default create secret docker-registry dockerhub-secret `
  --docker-server=https://index.docker.io/v1/ `
  --docker-username="$env:DOCKERHUB_USERNAME" `
  --docker-password="$env:DOCKERHUB_TOKEN" `
  --docker-email="$env:DOCKERHUB_EMAIL"
```

Use a Docker Hub access token, not the account password.

## Create Or Refresh ACR Secret

Use this if the worker image is hosted in Azure Container Registry:

```powershell
kubectl -n default delete secret acr-secret --ignore-not-found
kubectl -n default create secret docker-registry acr-secret `
  --docker-server=crjqmupr2v7hmzm.azurecr.io `
  --docker-username="$env:ACR_USERNAME" `
  --docker-password="$env:ACR_PASSWORD"
```

Then set the Helm/ArgoCD value to:

```yaml
imagePullSecrets:
  - name: acr-secret
```

## Verify The Deployment Uses The Secret

```powershell
kubectl -n default get deployment nexus-worker -o yaml | Select-String -Pattern "imagePullSecrets|dockerhub-secret|acr-secret" -Context 0,3
```

Expected:

```yaml
imagePullSecrets:
- name: dockerhub-secret
```

or:

```yaml
imagePullSecrets:
- name: acr-secret
```

## Force A Clean Worker Pull

After ArgoCD syncs the corrected spec:

```powershell
kubectl -n default rollout restart deployment nexus-worker
kubectl -n default rollout status deployment nexus-worker --timeout=180s
kubectl -n default get pods -l app=nexus-worker
```

If the pod still fails, inspect the latest event:

```powershell
kubectl -n default describe pod -l app=nexus-worker
```

## Most Likely Root Causes

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `unauthorized` | Secret missing, wrong namespace, expired token | Recreate secret in `nexus` namespace |
| `no basic auth credentials` | Pod spec does not reference secret | Add `imagePullSecrets` to chart/template |
| `manifest unknown` | Bad image tag | Push the image or update tag |
| `pull access denied` | Repo is private or wrong registry account | Use correct registry credentials |
| Works for API but not worker | Worker uses a different registry/image | Check `nexus-worker` image separately |

## ArgoCD Sync

After committing/pushing the chart fix:

```powershell
argocd app sync nexus-api
argocd app wait nexus-api --health --timeout 180
```

If the worker is managed by a separate ArgoCD app, sync that app instead.
