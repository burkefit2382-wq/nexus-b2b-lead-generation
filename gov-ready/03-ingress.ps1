param(
  [string]$Namespace = "ingress-nginx",
  [string]$NexusNamespace = "nexus"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$LocalKubectlDir = Join-Path $env:USERPROFILE ".azure-kubectl"
if (Test-Path (Join-Path $LocalKubectlDir "kubectl.exe")) {
  $env:Path = "$LocalKubectlDir;$env:Path"
}

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

function Require-Command($Name) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "$Name is required. Install it, then rerun this script."
  }
}

Require-Command kubectl
Require-Command helm

kubectl create namespace $Namespace --dry-run=client -o yaml | kubectl apply -f -

helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx | Out-Null
helm repo update | Out-Null
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx `
  --namespace $Namespace `
  --set controller.replicaCount=2 `
  --set controller.metrics.enabled=true `
  --set controller.service.externalTrafficPolicy=Local `
  --wait

kubectl apply -f (Join-Path $RepoRoot "platform/certificates/clusterissuer-letsencrypt-production.yaml")
kubectl apply -f (Join-Path $RepoRoot "k8s/ingress/nexus-ingress.yaml")
kubectl -n $NexusNamespace get ingress nexus-ingress

Write-Host "Ingress GOV baseline ready."
