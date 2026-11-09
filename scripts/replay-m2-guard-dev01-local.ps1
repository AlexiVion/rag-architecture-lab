$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Local Python .venv is missing." }
Write-Host "=== M2-GUARD-DEV-01 COMPLETE PYTEST REGRESSION SUITE ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "M2_GUARD_TESTS_FAILED" }
Write-Host "=== ARCHIVED 24-CASE GATE REPLAY - ZERO QWEN CALLS ==="
& $Python -m raglab.evaluation.m2_guard_dev01_replay --source-dir "runs/m2-synth01" --output "runs/m2-guard-dev01/counterfactual.json"
if ($LASTEXITCODE -ne 0) { throw "M2_GUARD_REPLAY_FAILED" }
Write-Host "M2_GUARD_DEV01_COMPLETE_RESEARCH_ONLY"
Write-Host "Existing pipeline, citation parser and original outputs unchanged."
