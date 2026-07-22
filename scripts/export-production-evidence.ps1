param(
  [string]$OutputDir = "",
  [string]$VaultName = "nexusvault28095",
  [string]$AcrName = "crjqmupr2v7hmzm"
)

$ErrorActionPreference = "Stop"

$Kubectl = $env:KUBECTL
if (-not $Kubectl) {
  $command = Get-Command kubectl -ErrorAction SilentlyContinue
  if ($command) {
    $Kubectl = $command.Source
  } elseif (Test-Path (Join-Path $HOME ".azure-kubectl/kubectl.exe")) {
    $Kubectl = Join-Path $HOME ".azure-kubectl/kubectl.exe"
  } else {
    throw "kubectl was not found. Set KUBECTL or install kubectl."
  }
}

if (-not $OutputDir) {
  $stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss")
  $OutputDir = Join-Path "evidence/nexus-production" $stamp
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

function Save-Text {
  param([string]$Path, [string]$Value)
  $Value | Out-File -FilePath (Join-Path $OutputDir $Path) -Encoding utf8
}

function Save-Command {
  param([string]$Path, [scriptblock]$Command)
  $target = Join-Path $OutputDir $Path
  try {
    & $Command | Out-File -FilePath $target -Encoding utf8
  } catch {
    "ERROR: $($_.Exception.Message)" | Out-File -FilePath $target -Encoding utf8
  }
}

$generatedAt = (Get-Date).ToUniversalTime().ToString("u")
Save-Text "README.md" @"
# NEXUS Production Evidence Export

Generated: $generatedAt

This folder intentionally stores inventory, status, and digest evidence only.
It does not export Kubernetes Secret values or Azure Key Vault secret values.

## Contents

- argocd-applications.txt: ArgoCD sync and health status.
- argocd-sync-status.png: image evidence generated from the live ArgoCD app table.
- aks-workloads.txt: NEXUS deployment, pod, ingress, certificate, and ExternalSecret status.
- https-health.txt: Public HTTPS health result.
- key-vault-secret-inventory.txt: Key Vault secret names only.
- acr-nexus-api-tags.json: API image tag/digest metadata.
- acr-nexus-worker-tags.json: worker image tag/digest metadata.
- certificate.yaml: cert-manager Certificate status.
- externalsecrets.yaml: ExternalSecret status.
- rollback-reference.md: release rollback reference.
"@

Save-Command "argocd-applications.txt" { & $Kubectl -n argocd get applications -o wide }
Save-Command "argocd-applications.json" { & $Kubectl -n argocd get applications -o json }
Save-Command "aks-workloads.txt" { & $Kubectl -n nexus get deploy,pods,svc,ingress,cronjob,pdb,resourcequota,limitrange,networkpolicy,certificate,externalsecret }
Save-Command "certificate.yaml" { & $Kubectl -n nexus get certificate nexuscloud-sh-tls -o yaml }
Save-Command "externalsecrets.yaml" { & $Kubectl -n nexus get externalsecret nexus-secrets nexus-keyvault-smoke -o yaml }
Save-Command "key-vault-secret-inventory.txt" { az keyvault secret list --vault-name $VaultName --query "[].{name:name,enabled:attributes.enabled,updated:attributes.updated}" -o table }
Save-Command "acr-nexus-api-tags.json" { az acr repository show-tags --name $AcrName --repository nexus-api --detail -o json }
Save-Command "acr-nexus-worker-tags.json" { az acr repository show-tags --name $AcrName --repository nexus-worker --detail -o json }
Save-Command "https-health.txt" { Invoke-WebRequest -UseBasicParsing -Uri "https://nexuscloud.sh/healthz" -TimeoutSec 20 | Select-Object StatusCode,Content | Format-List }
Save-Command "rollback-reference.md" { Get-Content -Raw "docs/production-operations-runbook.md" }

try {
  Add-Type -AssemblyName System.Drawing
  $argoApps = & $Kubectl -n argocd get applications -o json | ConvertFrom-Json
  $argoLines = New-Object System.Collections.Generic.List[string]
  $argoLines.Add(("{0,-20} {1,-12} {2,-12}" -f "APP", "SYNC", "HEALTH")) | Out-Null
  foreach ($app in $argoApps.items) {
    $argoLines.Add(("{0,-20} {1,-12} {2,-12}" -f $app.metadata.name, $app.status.sync.status, $app.status.health.status)) | Out-Null
  }
  $argoStatus = $argoLines -join [Environment]::NewLine
  $font = New-Object System.Drawing.Font("Consolas", 16)
  $titleFont = New-Object System.Drawing.Font("Segoe UI", 22, [System.Drawing.FontStyle]::Bold)
  $bitmap = New-Object System.Drawing.Bitmap(1200, 520)
  $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
  $graphics.Clear([System.Drawing.Color]::FromArgb(248, 250, 252))
  $brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(15, 23, 42))
  $mutedBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(71, 85, 105))
  $graphics.DrawString("NEXUS ArgoCD Sync Evidence", $titleFont, $brush, 40, 32)
  $graphics.DrawString("Generated: $generatedAt", $font, $mutedBrush, 40, 78)
  $graphics.DrawString($argoStatus, $font, $brush, 40, 130)
  $bitmap.Save((Join-Path $OutputDir "argocd-sync-status.png"), [System.Drawing.Imaging.ImageFormat]::Png)
  $graphics.Dispose()
  $bitmap.Dispose()
} catch {
  Save-Text "argocd-sync-status.txt" "PNG generation failed: $($_.Exception.Message)"
}

Write-Host "Evidence exported to $OutputDir"
