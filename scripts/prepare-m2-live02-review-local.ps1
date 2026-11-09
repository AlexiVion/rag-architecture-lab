$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Missing local Python .venv." }
Write-Host "=== M2-REVIEW-02 FULL REGRESSION SUITE ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "M2_REVIEW02_TESTS_FAILED" }
Write-Host "=== BUILD UNLABELLED REVIEW PACKETS FROM ARCHIVED QWEN ==="
& $Python -m raglab.evaluation.m2_review02 --original "runs/m2-live-v2/M2_LIVE02_20261104T185026616108Z.json" --output-dir "runs/m2-review02"
if ($LASTEXITCODE -ne 0) { throw "M2_REVIEW02_EXPORT_FAILED" }
Write-Host "M2_REVIEW02_PACKET_EXPORT_PASS"
Write-Host "No new model calls, no automatic semantic labels, no publication."
