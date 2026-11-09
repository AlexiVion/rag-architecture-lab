$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Local Python virtual environment not found." }

Write-Host "=== GRF-01 HYBRID RRF / GRAPH-HYBRID: FULL TEST SUITE ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "GRF01_FULL_TESTS_FAILED" }

Write-Host "=== FREEZE POLICY BEFORE OBSERVING NEW DEV SCORES ==="
& $Python -m raglab.graph.grf01_policy `
    --cohort "runs/graph-hybrid/GRF01_RESERVED_DEV_COHORT.json" `
    --output "runs/graph-hybrid/GRF01_POLICY_LOCK.json"
if ($LASTEXITCODE -ne 0) { throw "GRF01_POLICY_LOCK_FAILED" }

Write-Host "GRF01_HYBRID_POLICY_PREFLIGHT_PASS"
Write-Host "No embedding model loaded, no DEV cohort scored, no default changed."
