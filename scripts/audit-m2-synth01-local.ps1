$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Missing Python .venv" }
Write-Host "=== M2-SYNTH-01 FORENSIC AUDIT: FULL PYTEST ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "M2_SYNTH_AUDIT_TESTS_FAILED" }
Write-Host "=== VERIFY ORIGINAL SAVED 24 CASES WITHOUT QWEN ==="
& $Python -m raglab.evaluation.m2_synth01_audit --run-dir "runs/m2-synth01"
if ($LASTEXITCODE -ne 0) { throw "M2_SYNTH_ARCHIVE_AUDIT_FAILED" }
Write-Host "M2_SYNTH_ARCHIVE_INSPECTION_FINISHED"
Write-Host "No new inference. No changes to previous research outputs."
