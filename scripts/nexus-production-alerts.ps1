param(
  [int]$CertificateWarningDays = 14,
  [string]$PublicHealthUrl = "https://nexuscloud.sh/healthz"
)

$ErrorActionPreference = "Stop"
$failures = New-Object System.Collections.Generic.List[string]

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

function Add-Failure {
  param([string]$Message)
  $failures.Add($Message) | Out-Null
  Write-Host "FAIL $Message"
}

function Add-Pass {
  param([string]$Message)
  Write-Host "PASS $Message"
}

try {
  $rawApps = & $Kubectl -n argocd get applications -o json 2>&1
  $kubectlExitCode = $LASTEXITCODE
  if ($kubectlExitCode -ne 0) {
    $kubectlError = ($rawApps | Out-String).Trim()
    throw "kubectl get applications failed with exit code $kubectlExitCode`: $kubectlError"
  }

  $apps = ($rawApps | Out-String) | ConvertFrom-Json -ErrorAction Stop
  if (-not $apps.items -or $apps.items.Count -eq 0) {
    Add-Failure "No ArgoCD applications found in namespace argocd"
  } else {
    foreach ($app in $apps.items) {
      $health = $app.status.health.status ?? "Unknown"
      $sync = $app.status.sync.status ?? "Unknown"
      $operationPhase = $app.status.operationState.phase ?? "Unknown"
      if ($health -ne "Healthy" -or $sync -ne "Synced") {
        Add-Failure "ArgoCD app $($app.metadata.name) health=$health sync=$sync operationPhase=$operationPhase"
      } else {
        Add-Pass "ArgoCD app $($app.metadata.name) is Healthy and Synced (operationPhase=$operationPhase)"
      }
    }
  }
} catch {
  Add-Failure "Failed to query ArgoCD applications: $($_.Exception.Message)"
}

foreach ($deploymentName in @("nexus-api", "nexus-worker")) {
  $deployment = & $Kubectl -n nexus get deployment $deploymentName -o json | ConvertFrom-Json
  $desired = [int]($deployment.spec.replicas ?? 1)
  $available = [int]($deployment.status.availableReplicas ?? 0)
  if ($available -lt $desired) {
    Add-Failure "$deploymentName available replicas $available/$desired"
  } else {
    Add-Pass "$deploymentName available replicas $available/$desired"
  }
}

$certificate = & $Kubectl -n nexus get certificate nexuscloud-sh-tls -o json | ConvertFrom-Json
$readyCondition = $certificate.status.conditions | Where-Object { $_.type -eq "Ready" } | Select-Object -First 1
if ($readyCondition.status -ne "True") {
  Add-Failure "TLS certificate nexuscloud-sh-tls is not Ready"
} else {
  $notAfter = [DateTimeOffset]::Parse($certificate.status.notAfter)
  $daysRemaining = ($notAfter - [DateTimeOffset]::UtcNow).TotalDays
  if ($daysRemaining -lt $CertificateWarningDays) {
    Add-Failure "TLS certificate expires in $([Math]::Round($daysRemaining, 1)) days"
  } else {
    Add-Pass "TLS certificate Ready; expires $($notAfter.UtcDateTime.ToString('u'))"
  }
}

foreach ($externalSecretName in @("nexus-secrets", "nexus-keyvault-smoke")) {
  $externalSecret = & $Kubectl -n nexus get externalsecret $externalSecretName -o json | ConvertFrom-Json
  $condition = $externalSecret.status.conditions | Where-Object { $_.type -eq "Ready" } | Select-Object -First 1
  if ($condition.status -ne "True") {
    Add-Failure "ExternalSecret $externalSecretName is not Ready: $($condition.reason) $($condition.message)"
  } else {
    Add-Pass "ExternalSecret $externalSecretName is Ready"
  }
}

try {
  $response = Invoke-WebRequest -UseBasicParsing -Uri $PublicHealthUrl -TimeoutSec 20
  if ($response.StatusCode -ne 200 -or $response.Content -notmatch '"ok"\s*:\s*true') {
    Add-Failure "Uptime check failed: $PublicHealthUrl returned $($response.StatusCode)"
  } else {
    Add-Pass "Uptime check passed: $PublicHealthUrl"
  }
} catch {
  Add-Failure "Uptime check exception: $($_.Exception.Message)"
}

if ($failures.Count -gt 0) {
  Write-Error ("NEXUS production alert failures:`n" + ($failures -join "`n"))
  exit 1
}

Write-Host "NEXUS production alerts passed."
