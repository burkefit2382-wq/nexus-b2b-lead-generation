param(
  [string]$Repository = "burkefit2382-wq/nexus-b2b-lead-generation",
  [string]$Branch = "main",
  [string]$PolicyPath = ".github/branch-protection-main.json"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $PolicyPath)) {
  throw "Policy file not found: $PolicyPath"
}

$token = $env:GH_TOKEN
if (-not $token) {
  $token = $env:GITHUB_TOKEN
}

if (-not $token) {
  $gh = Get-Command gh -ErrorAction SilentlyContinue
  if ($gh) {
    try {
      gh auth status 2>$null | Out-Null
      $token = gh auth token
    } catch {
      $token = $null
    }
  }
}

if (-not $token) {
  throw "No GitHub admin token available. Set GH_TOKEN/GITHUB_TOKEN with repo administration permission or run gh auth login."
}

$body = Get-Content -Raw $PolicyPath
$uri = "https://api.github.com/repos/$Repository/branches/$Branch/protection"

$headers = @{
  Authorization = "Bearer $token"
  Accept = "application/vnd.github+json"
  "X-GitHub-Api-Version" = "2022-11-28"
}

Invoke-RestMethod -Method Put -Uri $uri -Headers $headers -Body $body -ContentType "application/json" | Out-Null
Write-Host "Branch protection applied to $Repository/$Branch"
