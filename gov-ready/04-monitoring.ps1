param(
  [string]$Namespace = "monitoring"
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

Require-Command kubectl
Require-Command helm

kubectl create namespace $Namespace --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace $Namespace pod-security.kubernetes.io/enforce=baseline pod-security.kubernetes.io/audit=restricted pod-security.kubernetes.io/warn=restricted --overwrite

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts | Out-Null
helm repo add grafana https://grafana.github.io/helm-charts | Out-Null
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts | Out-Null
helm repo update | Out-Null

helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack `
  --namespace $Namespace `
  --set grafana.enabled=true `
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false `
  --set prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues=false `
  --wait

helm upgrade --install loki grafana/loki `
  --namespace $Namespace `
  --wait

helm upgrade --install promtail grafana/promtail `
  --namespace $Namespace `
  --set config.clients[0].url=http://loki-gateway.monitoring.svc.cluster.local/loki/api/v1/push `
  --wait

helm upgrade --install opentelemetry-collector open-telemetry/opentelemetry-collector `
  --namespace $Namespace `
  --set mode=deployment `
  --wait

kubectl -n $Namespace get pods
Write-Host "Monitoring GOV baseline ready."
