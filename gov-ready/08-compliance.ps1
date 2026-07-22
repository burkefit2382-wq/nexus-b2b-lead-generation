param(
  [string]$ResourceGroup = "nexus-rg",
  [string]$ClusterName = "nexus-aks",
  [string]$WorkspaceName = "nexus-law",
  [string]$Location = "canadacentral",
  [string]$Namespace = "nexus",
  [string]$DiagnosticSettingName = "nexus-aks-gov-audit",
  [switch]$RebindMonitoringAddon
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
$resourceGroupLocation = az group show --name $ResourceGroup --query location -o tsv --only-show-errors 2>$null
if (-not $resourceGroupLocation) {
  az group create --name $ResourceGroup --location $Location --only-show-errors | Out-Null
  $resourceGroupLocation = $Location
} else {
  Write-Host "Resource group already exists in $resourceGroupLocation"
}
az provider register --namespace Microsoft.OperationalInsights --wait --only-show-errors | Out-Null
az provider register --namespace Microsoft.Insights --wait --only-show-errors | Out-Null

$cluster = az aks show --resource-group $ResourceGroup --name $ClusterName -o json --only-show-errors | ConvertFrom-Json
$clusterLocation = $cluster.location
$clusterId = $cluster.id

$workspaceJson = az monitor log-analytics workspace list --resource-group $ResourceGroup --query "[?name=='$WorkspaceName'] | [0]" -o json --only-show-errors
if (-not $workspaceJson -or $workspaceJson -eq "null") {
  az monitor log-analytics workspace create --resource-group $ResourceGroup --workspace-name $WorkspaceName --location $clusterLocation --only-show-errors | Out-Null
  $effectiveWorkspaceName = $WorkspaceName
} else {
  $workspace = $workspaceJson | ConvertFrom-Json
  if ($workspace.location -ne $clusterLocation) {
    $effectiveWorkspaceName = "$WorkspaceName-$clusterLocation"
    Write-Host "Workspace $WorkspaceName is in $($workspace.location); using cluster-region workspace $effectiveWorkspaceName in $clusterLocation."
    $regionalWorkspaceJson = az monitor log-analytics workspace list --resource-group $ResourceGroup --query "[?name=='$effectiveWorkspaceName'] | [0]" -o json --only-show-errors
    if (-not $regionalWorkspaceJson -or $regionalWorkspaceJson -eq "null") {
      az monitor log-analytics workspace create --resource-group $ResourceGroup --workspace-name $effectiveWorkspaceName --location $clusterLocation --only-show-errors | Out-Null
    }
  } else {
    $effectiveWorkspaceName = $WorkspaceName
  }
}

$workspaceId = az monitor log-analytics workspace show --resource-group $ResourceGroup --workspace-name $effectiveWorkspaceName --query id -o tsv
$monitoringEnabled = az aks show --resource-group $ResourceGroup --name $ClusterName --query "addonProfiles.omsagent.enabled" -o tsv --only-show-errors
if ($monitoringEnabled -eq "true") {
  Write-Host "AKS monitoring addon is already enabled."
  if ($RebindMonitoringAddon) {
    Write-Host "Rebinding AKS monitoring addon to $effectiveWorkspaceName."
    az aks disable-addons --resource-group $ResourceGroup --name $ClusterName --addons monitoring --only-show-errors | Out-Null
    az aks enable-addons --resource-group $ResourceGroup --name $ClusterName --addons monitoring --workspace-resource-id $workspaceId --only-show-errors | Out-Null
  }
} else {
  az aks enable-addons --resource-group $ResourceGroup --name $ClusterName --addons monitoring --workspace-resource-id $workspaceId --only-show-errors | Out-Null
}

$logs = ConvertTo-Json -InputObject @(
  @{ category = "kube-apiserver"; enabled = $true },
  @{ category = "kube-audit"; enabled = $true },
  @{ category = "kube-audit-admin"; enabled = $true },
  @{ category = "kube-controller-manager"; enabled = $true },
  @{ category = "kube-scheduler"; enabled = $true },
  @{ category = "cluster-autoscaler"; enabled = $true },
  @{ category = "guard"; enabled = $true }
) -Compress -Depth 4

$metrics = ConvertTo-Json -InputObject @(
  @{ category = "AllMetrics"; enabled = $true }
) -Compress -Depth 4

az monitor diagnostic-settings create `
  --name $DiagnosticSettingName `
  --resource $clusterId `
  --workspace $workspaceId `
  --logs $logs `
  --metrics $metrics `
  --only-show-errors | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "Failed to create AKS diagnostic setting $DiagnosticSettingName."
}

kubectl annotate namespace $Namespace compliance.nexuscloud.sh/tls-required="true" --overwrite
kubectl annotate namespace $Namespace compliance.nexuscloud.sh/keyvault-only-secrets="true" --overwrite
kubectl annotate namespace $Namespace compliance.nexuscloud.sh/signed-images-required="true" --overwrite
kubectl annotate namespace $Namespace compliance.nexuscloud.sh/azure-monitor-workspace="$effectiveWorkspaceName" --overwrite
kubectl annotate namespace $Namespace compliance.nexuscloud.sh/aks-diagnostics="$DiagnosticSettingName" --overwrite

kubectl get clustersecretstore nexus-azure-keyvault
kubectl -n $Namespace get certificate,externalsecret,secretstore 2>$null
az monitor diagnostic-settings show --name $DiagnosticSettingName --resource $clusterId --query "{name:name,workspaceId:workspaceId,logs:logs[?enabled].category,metrics:metrics[?enabled].category}" -o json
if ($LASTEXITCODE -ne 0) {
  throw "AKS diagnostic setting $DiagnosticSettingName was not found after creation."
}
Write-Host "Compliance GOV baseline ready."
