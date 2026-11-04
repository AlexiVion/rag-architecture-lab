$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Raglab = Join-Path $RepoRoot ".venv\Scripts\raglab.exe"
if (-not (Test-Path $Python) -or -not (Test-Path $Raglab)) {
    throw "Missing local Python virtual environment."
}
Write-Host "=== M2 NLI DIAGNOSTICS: TESTS ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "TESTS_FAILED" }

$suite = Get-ChildItem "runs\dev-cases\M2-DEV-EVIDENCE-01_*" -Directory -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending |
    Select-Object -First 1
if (-not $suite) { throw "No M2 TRAIN suite found." }
Write-Host "=== AUTOMATIC NLI CHECKS, ZERO QUESTIONS ==="
& $Raglab diagnose-nli --suite $suite.FullName
if ($LASTEXITCODE -ne 0) { throw "NLI_DIAGNOSE_FAILED" }
Write-Host "M2_NLI_DIAGNOSIS_COMPLETE"
