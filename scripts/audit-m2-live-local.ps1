$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Missing local .venv Python." }

Write-Host "=== M2 ARCHIVED QWEN AUDIT: FULL REGRESSION SUITE ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "M2_AUDIT_TESTS_FAILED" }

Write-Host "=== ORIGINAL FOUR-CONTROL QWEN OUTPUT: NO INFERENCE ==="
& $Python -m raglab.evaluation.m2_live_audit --input "runs/m2-live/M2_LIVE_20261104T182515461187Z.json" --output-dir "runs/m2-live"
if ($LASTEXITCODE -ne 0) { throw "M2_ARCHIVED_RUN_AUDIT_FAILED" }
Write-Host "M2_SAVED_OUTPUT_AUDITED_NO_MODEL_REEXECUTION"
