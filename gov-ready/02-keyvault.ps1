param(
  [string]$ResourceGroup = "nexus-rg",
  [string]$Location = "canadacentral",
  [string]$KeyVaultName = "nexusvault28095",
  [string]$KeyVaultResourceGroup = "",
  [string]$Namespace = "nexus",
  [string]$ExternalSecretsServiceAccount = "nexus-external-secrets"
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

function Convert-SecureStringToPlainText($Value) {
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Value)
  try {
    [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
  } finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
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
  Write-Host "Resource group $ResourceGroup already exists in $resourceGroupLocation"
}

$vaultQuery = "[?name=='$KeyVaultName'] | [0]"
if ($KeyVaultResourceGroup) {
  $vaultJson = az keyvault list --resource-group $KeyVaultResourceGroup --query $vaultQuery -o json --only-show-errors
} else {
  $vaultJson = az keyvault list --query $vaultQuery -o json --only-show-errors
}

if (-not $vaultJson -or $vaultJson -eq "null") {
  $effectiveKeyVaultResourceGroup = if ($KeyVaultResourceGroup) { $KeyVaultResourceGroup } else { $ResourceGroup }
  $keyVaultResourceGroupLocation = az group show --name $effectiveKeyVaultResourceGroup --query location -o tsv --only-show-errors 2>$null
  if (-not $keyVaultResourceGroupLocation) {
    az group create --name $effectiveKeyVaultResourceGroup --location $resourceGroupLocation --only-show-errors | Out-Null
    $keyVaultResourceGroupLocation = $resourceGroupLocation
  }
  az keyvault create `
    --name $KeyVaultName `
    --resource-group $effectiveKeyVaultResourceGroup `
    --location $keyVaultResourceGroupLocation `
    --enable-rbac-authorization false `
    --sku standard `
    --only-show-errors | Out-Null
} else {
  $vault = $vaultJson | ConvertFrom-Json
  $effectiveKeyVaultResourceGroup = $vault.resourceGroup
  Write-Host "Key Vault already exists: $KeyVaultName in resource group $effectiveKeyVaultResourceGroup ($($vault.location))"
}

$secretNames = @(
  "nexus-prod-DATABASE-URL",
  "nexus-prod-HUBSPOT-ACCESS-TOKEN",
  "nexus-prod-HUBSPOT-PORTAL-ID",
  "nexus-prod-JWT-SECRET",
  "nexus-prod-PRICE-ID",
  "nexus-prod-RESEND-API-KEY",
  "nexus-prod-RESEND-FROM",
  "nexus-prod-STRIPE-SECRET-KEY",
  "nexus-prod-STRIPE-WEBHOOK-SECRET",
  "nexus-prod-WAITLIST-NOTIFY-TO"
)

foreach ($secretName in $secretNames) {
  $exists = az keyvault secret show --vault-name $KeyVaultName --name $secretName --query id -o tsv 2>$null
  if (-not $exists) {
    $value = Read-Host "Enter value for $secretName" -AsSecureString
    az keyvault secret set --vault-name $KeyVaultName --name $secretName --value (Convert-SecureStringToPlainText $value) --only-show-errors | Out-Null
  } else {
    Write-Host "Secret exists: $secretName"
  }
}

kubectl create namespace $Namespace --dry-run=client -o yaml | kubectl apply -f -
kubectl -n $Namespace create serviceaccount $ExternalSecretsServiceAccount --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f (Join-Path $RepoRoot "platform/secrets/nexus-keyvault-serviceaccount.yaml")
kubectl apply -f (Join-Path $RepoRoot "platform/secrets/azure-key-vault-store.yaml")
kubectl apply -f (Join-Path $RepoRoot "platform/secrets/nexus-production-external-secret.yaml")
kubectl -n $Namespace get externalsecret nexus-secrets

Write-Host "Key Vault GOV secret baseline ready: $KeyVaultName"
