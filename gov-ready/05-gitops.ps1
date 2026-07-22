param(
  [string]$Namespace = "argocd"
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

kubectl create namespace $Namespace --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n $Namespace --server-side --force-conflicts -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

kubectl -n $Namespace rollout status deployment/argocd-server --timeout=300s

kubectl apply -f (Join-Path $RepoRoot "argocd/cert-manager-app.yaml")
kubectl apply -f (Join-Path $RepoRoot "argocd/external-secrets-app.yaml")
kubectl apply -f (Join-Path $RepoRoot "argocd/nexus-platform-app.yaml")
kubectl apply -f (Join-Path $RepoRoot "argocd/nexus-k8s-app.yaml")

kubectl -n $Namespace get applications.argoproj.io
Write-Host "GitOps GOV baseline ready. GUI: kubectl -n argocd port-forward svc/argocd-server 18443:443"
