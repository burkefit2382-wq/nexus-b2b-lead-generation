param(
  [string]$Namespace = "nexus"
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
kubectl label namespace $Namespace pod-security.kubernetes.io/enforce=baseline pod-security.kubernetes.io/audit=restricted pod-security.kubernetes.io/warn=restricted --overwrite

kubectl apply -f (Join-Path $RepoRoot "k8s/policies/nexus-network-policies.yaml")
kubectl apply -f (Join-Path $RepoRoot "k8s/policies/nexus-poddisruptionbudgets.yaml")
kubectl apply -f (Join-Path $RepoRoot "k8s/policies/nexus-resource-controls.yaml")
kubectl apply -f (Join-Path $RepoRoot "platform/policies/nexus-image-admission-policy.yaml")

kubectl -n $Namespace create role nexus-readonly `
  --verb=get,list,watch `
  --resource=pods,services,deployments,replicasets,jobs,cronjobs,configmaps,events `
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n $Namespace create serviceaccount nexus-automation --dry-run=client -o yaml | kubectl apply -f -
kubectl -n $Namespace create rolebinding nexus-automation-readonly `
  --role=nexus-readonly `
  --serviceaccount="${Namespace}:nexus-automation" `
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n $Namespace get networkpolicy
kubectl -n $Namespace get role,rolebinding
Write-Host "Security GOV baseline ready."
