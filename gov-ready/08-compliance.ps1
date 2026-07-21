param(
  [string]$ResourceGroup = "nexus-rg",
  [string]$ClusterName = "nexus-aks",
  [string]$WorkspaceName = "nexus-law",
  [string]$Location = "canadacentral",
  [string]$Namespace = "nexus"
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

$workspaceJson = az monitor log-analytics workspace list --resource-group $ResourceGroup --query "[?name=='$WorkspaceName'] | [0]" -o json --only-show-errors
if (-not $workspaceJson -or $workspaceJson -eq "null") {
  az monitor log-analytics workspace create --resource-group $ResourceGroup --workspace-name $WorkspaceName --location $resourceGroupLocation --only-show-errors | Out-Null
}

$workspaceId = az monitor log-analytics workspace show --resource-group $ResourceGroup --workspace-name $WorkspaceName --query id -o tsv
$monitoringEnabled = az aks show --resource-group $ResourceGroup --name $ClusterName --query "addonProfiles.omsagent.enabled" -o tsv --only-show-errors
if ($monitoringEnabled -eq "true") {
  Write-Host "AKS monitoring addon is already enabled."
} else {
  az aks enable-addons --resource-group $ResourceGroup --name $ClusterName --addons monitoring --workspace-resource-id $workspaceId --only-show-errors | Out-Null
}

kubectl annotate namespace $Namespace compliance.nexuscloud.sh/tls-required="true" --overwrite
kubectl annotate namespace $Namespace compliance.nexuscloud.sh/keyvault-only-secrets="true" --overwrite
kubectl annotate namespace $Namespace compliance.nexuscloud.sh/signed-images-required="true" --overwrite

kubectl get clustersecretstore nexus-azure-keyvault
kubectl -n $Namespace get certificate,externalsecret,secretstore 2>$null
Write-Host "Compliance GOV baseline ready."
