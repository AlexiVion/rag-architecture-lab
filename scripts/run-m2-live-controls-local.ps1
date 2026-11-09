$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Local Python environment missing." }

Write-Host "=== M2-LIVE-01: FULL PYTEST REGRESSION SUITE ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "M2_LIVE_TESTS_FAILED" }

Write-Host "=== M2-LIVE-01: REAL QWEN / ORIGINAL FICTIONAL CONTROLS ==="
Write-Host "Four fixed cases; three calls to CPU Qwen; one no-context generator skip."
Write-Host "No SciFact TEST, graph benchmark rerun, paid API or manual prompts."
& $Python -m raglab.evaluation.m2_live_smoke --output-dir "runs/m2-live"
if ($LASTEXITCODE -ne 0) { throw "M2_LIVE_SMOKE_FAILED" }

Write-Host "M2_LIVE_LOCAL_OPERATIONAL_SMOKE_FINISHED"
Write-Host "IMPORTANT: Semantic support, answer relevance and scientific accuracy remain UNASSESSED."
