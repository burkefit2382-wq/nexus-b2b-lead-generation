$ErrorActionPreference = "SilentlyContinue"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$logPath = Join-Path $root "data\scrapers\stopper_8pm.log"
$workers = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq "python.exe" -and $_.CommandLine -match "tampa_bay_lead_worker.py"
}

foreach ($worker in $workers) {
    Stop-Process -Id $worker.ProcessId -Force
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
$ids = ($workers | ForEach-Object { $_.ProcessId }) -join ", "
"$timestamp stopped scraper workers: $ids" | Out-File -FilePath $logPath -Append -Encoding utf8
