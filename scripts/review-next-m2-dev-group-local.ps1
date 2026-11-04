$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Raglab = Join-Path $RepoRoot ".venv\Scripts\raglab.exe"
if (-not (Test-Path $Python) -or -not (Test-Path $Raglab)) {
    throw "Missing local virtual environment."
}
Write-Host "=== M2 DEV BATCH TESTS ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "PYTEST_FAILED" }

$suite = Get-ChildItem "runs\dev-cases\M2-DEV-EVIDENCE-01_*" -Directory -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending |
    Select-Object -First 1
if (-not $suite) {
    throw "No M2 train suite found. Run prepare-m2-dev-cases-local.ps1 first."
}
Write-Host "=== M2 THREE BLIND HUMAN REVIEWS ==="
Write-Host "Suite: $($suite.FullName)"
Write-Host "To mark uncertainty choose u; no outcomes are prefilled."
& $Raglab review-dev-batch --suite $suite.FullName --max-cases 3
if ($LASTEXITCODE -ne 0) { throw "DEV_REVIEW_BATCH_FAILED" }
Write-Host "M2_DEV_REVIEW_BATCH_FINISHED"
