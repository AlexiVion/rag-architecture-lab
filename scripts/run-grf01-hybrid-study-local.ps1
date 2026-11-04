$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Local Python environment not found." }

Write-Host "=== GRF-01 SINGLE PASS: FULL REGRESSION SUITE ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "GRF01_TESTS_FAILED" }

Write-Host "=== VERIFY FROZEN COHORT & POLICY BEFORE MODEL DOWNLOAD ==="
& $Python -m raglab.graph.grf01_policy
if ($LASTEXITCODE -ne 0) { throw "GRF01_POLICY_LOCK_FAILED" }

Write-Host "=== ONE PASS ON THE 60 RESERVED DEV CASES ==="
Write-Host "Local pinned CPU embedding weights may download at first use."
Write-Host "No user prompts, Qwen, paid APIs, TEST qrels or tuning."
& $Python -m raglab.graph.grf01_study
if ($LASTEXITCODE -ne 0) { throw "GRF01_SEALED_STUDY_FAILED" }

Write-Host "GRF01_ONE_PASS_STUDY_COMPLETE"
Write-Host "Results are local and will not be overwritten by a repeat command."
