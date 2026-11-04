$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Python .venv not found." }
Write-Host "=== M2-GUARD-STRESS-01 FULL TEST SUITE ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "M2_GUARD_STRESS_TESTS_FAILED" }
Write-Host "=== AUTHORED 40-CASE OFFLINE GUARD STRESS ==="
& $Python -m raglab.evaluation.m2_guard_stress01 --output "runs/m2-guard-stress01/report.json"
if ($LASTEXITCODE -ne 0) { throw "M2_GUARD_STRESS_RUN_FAILED" }
Write-Host "M2_GUARD_STRESS01_FINISHED"
Write-Host "Zero Qwen calls, no network requests and no publications."

