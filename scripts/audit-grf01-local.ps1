$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Local Python environment missing." }

Write-Host "=== GRF-01 SAVED-RESULT AUDIT: FULL REGRESSION TESTS ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "GRF01_AUDIT_TESTS_FAILED" }

Write-Host "=== AUDIT FROZEN 60-QUERY RESULT WITHOUT RERUNNING THE MODEL ==="
& $Python -m raglab.graph.grf01_audit
if ($LASTEXITCODE -ne 0) { throw "GRF01_SAVED_REPORT_AUDIT_FAILED" }

Write-Host "GRF01_POSTRUN_AUDIT_COMPLETE"
Write-Host "Study and original cohort were not changed or rerun."
