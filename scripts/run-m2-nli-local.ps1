$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Raglab = Join-Path $RepoRoot ".venv\Scripts\raglab.exe"
if (-not (Test-Path $Python) -or -not (Test-Path $Raglab)) {
    throw "Local environment not found."
}

Write-Host "=== M2 CPU NLI PILOT: TESTS ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "PYTEST_FAILED" }

$suite = Get-ChildItem "runs\dev-cases\M2-DEV-EVIDENCE-01_*" -Directory -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending |
    Select-Object -First 1
if (-not $suite) {
    throw "No TRAIN suite found. Run prepare-m2-dev-cases-local.ps1 first."
}
Write-Host "=== M2 LOCAL NLI PREDICTIONS (NO USER PROMPTS) ==="
& $Raglab nli-dev-pilot --suite $suite.FullName --batch-size 2
if ($LASTEXITCODE -ne 0) { throw "NLI_PILOT_FAILED" }

Write-Host "M2_NLI_PILOT_COMPLETED"
Write-Host "Prediction labels are UNCALIBRATED, NOT scientific truth."
