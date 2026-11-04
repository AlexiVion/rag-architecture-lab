# Windows PowerShell 5.1 may misread UTF-8 without BOM; keep this file ASCII-only.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Missing local .venv." }
Write-Host "=== M2 V2 CITATION PARSER: FULL PYTEST ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "M2_CITATION_V2_TESTS_FAILED" }
Write-Host "=== REPLAY EXISTING M2-LIVE-02 REPORT - ZERO MODEL CALLS ==="
& $Python -m raglab.evaluation.m2_live_v2_replay --original "runs/m2-live-v2/M2_LIVE02_20261104T185026616108Z.json" --output "runs/m2-parser-replay/M2_LIVE02_SYNTAX_REPLAY.json"
if ($LASTEXITCODE -ne 0) { throw "M2_CITATION_V2_REPLAY_FAILED" }
Write-Host "M2_CITATION_V2_OFFLINE_REPLAY_PASS"
Write-Host "Archived result unchanged. No Qwen invocation. No publication."
