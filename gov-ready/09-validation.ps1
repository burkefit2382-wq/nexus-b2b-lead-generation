param(
  [string]$Namespace = "nexus",
  [string]$ArgoNamespace = "argocd",
  [string]$PublicBaseUrl = "https://nexuscloud.sh"
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

function Assert-Http($Name, $Url, $Expected) {
  Write-Host "Checking $Name -> $Url"
  $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 30
  if ($response.StatusCode -ne 200 -or $response.Content -notmatch $Expected) {
    throw "$Name failed. Expected HTTP 200 and body containing '$Expected'."
  }
}

Require-Command kubectl

kubectl -n $Namespace get deploy nexus-api nexus-worker
kubectl -n $Namespace get cronjob nexus-osint-scraper-quality nexus-internal-health
kubectl -n $ArgoNamespace get applications.argoproj.io

Assert-Http "public health" "$PublicBaseUrl/health" "ok"
Assert-Http "public readiness" "$PublicBaseUrl/ready" "ready"
Assert-Http "public metrics" "$PublicBaseUrl/metrics" "nexus_service_up"

$apps = kubectl -n $ArgoNamespace get applications.argoproj.io -o json | ConvertFrom-Json
foreach ($app in $apps.items) {
  if ($app.status.sync.status -ne "Synced" -or $app.status.health.status -ne "Healthy") {
    throw "Argo CD app $($app.metadata.name) is $($app.status.sync.status)/$($app.status.health.status)"
  }
}

kubectl -n $Namespace get pods
Write-Host "GOV validation complete. NEXUS is operational against the Phase 1 health/readiness/metrics baseline."
