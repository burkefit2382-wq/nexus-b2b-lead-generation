param(
  [string]$Namespace = "nexus",
  [string]$ArgoNamespace = "argocd",
  [switch]$Wait
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

function Wait-ArgoApplication($Name, [int]$TimeoutSeconds = 600) {
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    $app = kubectl -n $ArgoNamespace get application $Name -o json 2>$null | ConvertFrom-Json
    if ($app) {
      $sync = $app.status.sync.status
      $health = $app.status.health.status
      Write-Host "$Name => sync=$sync health=$health"
      if ($sync -eq "Synced" -and $health -eq "Healthy") {
        return
      }
    }
    Start-Sleep -Seconds 10
  }
  throw "Timed out waiting for Argo CD application $Name to become Synced/Healthy."
}

kubectl apply -f (Join-Path $RepoRoot "argocd/cert-manager-app.yaml")
kubectl apply -f (Join-Path $RepoRoot "argocd/external-secrets-app.yaml")
kubectl apply -f (Join-Path $RepoRoot "argocd/nexus-platform-app.yaml")
kubectl apply -f (Join-Path $RepoRoot "argocd/nexus-k8s-app.yaml")

foreach ($app in @("cert-manager", "external-secrets", "nexus-platform", "nexus-k8s")) {
  kubectl -n $ArgoNamespace annotate application $app argocd.argoproj.io/refresh=hard --overwrite
}

if ($Wait) {
  Wait-ArgoApplication "cert-manager"
  Wait-ArgoApplication "external-secrets"
  Wait-ArgoApplication "nexus-platform"
  Wait-ArgoApplication "nexus-k8s"
}

kubectl -n $ArgoNamespace get applications.argoproj.io
kubectl -n $Namespace get deploy,svc,ingress,cronjob
Write-Host "NEXUS deployment is controlled by Argo CD. Workloads are reconciled from GitOps applications, not direct kubectl apply."
