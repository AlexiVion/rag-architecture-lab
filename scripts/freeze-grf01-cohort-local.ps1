$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Local Python environment missing." }
Write-Host "=== GRF-01 COHORT FREEZE: FULL REGRESSION TESTS ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "GRF01_TESTS_FAILED" }
Write-Host "=== VERIFY EXPOSED STUDY & RESERVE 60 DISJOINT DEV QUERIES ==="
& $Python -m raglab.graph.grf01_cohort
if ($LASTEXITCODE -ne 0) { throw "GRF01_COHORT_FREEZE_FAILED" }
Write-Host "GRF01_NO_PROMPT_COHORT_READY"
Write-Host "This does not run any new model, retrieval study, or semantic evaluator."
