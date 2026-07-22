param(
  [string]$ResourceGroup = "nexus-rg",
  [string]$ClusterName = "nexus-aks",
  [string]$Location = "canadacentral",
  [string]$NodeVmSize = "Standard_D4s_v5",
  [int]$NodeCount = 3
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$LocalKubectlDir = Join-Path $env:USERPROFILE ".azure-kubectl"
if (Test-Path (Join-Path $LocalKubectlDir "kubectl.exe")) {
  $env:Path = "$LocalKubectlDir;$env:Path"
}

function Require-Command($Name) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "$Name is required. Install it, then rerun this script."
  }
}

Require-Command az
Require-Command kubectl

az account show --only-show-errors | Out-Null
az group create --name $ResourceGroup --location $Location --only-show-errors | Out-Null

$cluster = az aks show --resource-group $ResourceGroup --name $ClusterName --only-show-errors 2>$null | ConvertFrom-Json
if (-not $cluster) {
  az aks create `
    --resource-group $ResourceGroup `
    --name $ClusterName `
    --location $Location `
    --node-count $NodeCount `
    --node-vm-size $NodeVmSize `
    --enable-managed-identity `
    --enable-aad `
    --enable-azure-rbac `
    --network-plugin azure `
    --network-plugin-mode overlay `
    --network-policy calico `
    --generate-ssh-keys `
    --only-show-errors | Out-Null
} else {
  Write-Host "AKS cluster already exists: $ClusterName"
}

az aks update `
  --resource-group $ResourceGroup `
  --name $ClusterName `
  --enable-azure-rbac `
  --only-show-errors | Out-Null

az aks get-credentials --resource-group $ResourceGroup --name $ClusterName --overwrite-existing --only-show-errors | Out-Null

kubectl create namespace nexus --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace staging --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace dev --dry-run=client -o yaml | kubectl apply -f -

kubectl label namespace nexus pod-security.kubernetes.io/enforce=baseline pod-security.kubernetes.io/audit=restricted pod-security.kubernetes.io/warn=restricted --overwrite
kubectl label namespace staging pod-security.kubernetes.io/enforce=baseline pod-security.kubernetes.io/audit=restricted pod-security.kubernetes.io/warn=restricted --overwrite
kubectl label namespace dev pod-security.kubernetes.io/enforce=baseline pod-security.kubernetes.io/audit=restricted pod-security.kubernetes.io/warn=restricted --overwrite

Write-Host "AKS GOV baseline ready: $ResourceGroup/$ClusterName"
