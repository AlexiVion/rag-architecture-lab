$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Missing Python virtual environment." }

Write-Host "=== M2-LIVE-02: FULL TEST SUITE BEFORE INFERENCE ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "M2_LIVE02_REGRESSION_TESTS_FAILED" }

Write-Host "=== M2-LIVE-02: VERSIONED PROMPT DEVELOPMENT ==="
Write-Host "Three local CPU Qwen generations, known fictional development controls."
Write-Host "Saved M2-LIVE-01 SHA verification before loading Qwen."
Write-Host "No API charges, no SciFact TEST, no answer publication."
& $Python -m raglab.evaluation.m2_live_v2 --original "runs/m2-live/M2_LIVE_20261104T182515461187Z.json" --output-dir "runs/m2-live-v2"
if ($LASTEXITCODE -ne 0) { throw "M2_LIVE02_RUN_FAILED" }
Write-Host "M2_LIVE02_COMPLETED_RESEARCH_ONLY"
Write-Host "No previous experiment overwritten; all generated claims held for review."
