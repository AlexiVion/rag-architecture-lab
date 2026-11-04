$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Raglab = Join-Path $RepoRoot ".venv\Scripts\raglab.exe"
if (-not (Test-Path $Python) -or -not (Test-Path $Raglab)) {
    throw "Local Python environment is missing."
}

Write-Host "=== M2 AUTOMATIC TRAIN AUDIT: TESTS ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "PYTEST_FAILED" }

$suite = Get-ChildItem "runs\dev-cases\M2-DEV-EVIDENCE-01_*" -Directory -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending |
    Select-Object -First 1
if (-not $suite) {
    throw "No M2 TRAIN case suite exists. Run prepare-m2-dev-cases-local.ps1 first."
}

Write-Host "=== M2 AUTOMATIC TRAIN AUDIT (NO PROMPTS) ==="
& $Raglab audit-dev-suite --suite $suite.FullName
if ($LASTEXITCODE -ne 0) { throw "AUTOMATIC_AUDIT_FAILED" }
Write-Host "M2_AUTO_AUDIT_COMPLETE"
Write-Host "All deterministic checks finished without human input or models."
Write-Host "Semantic truth and adequacy still require independent validation."
