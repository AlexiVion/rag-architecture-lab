$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Local Python .venv is missing." }
Write-Host "=== M2-SYNTH-01 FULL REGRESSION TESTS ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "M2_SYNTH01_TESTS_FAILED" }
Write-Host "=== FROZEN 24-CASE SYNTHETIC QA CONTROL STUDY ==="
Write-Host "Six each: sufficient, irrelevant, conflicting, no-context."
Write-Host "Up to 18 Qwen CPU calls; cases checkpoint individually."
Write-Host "Prior complete case files will not be regenerated."
Write-Host "Model weights may be loaded from local cache; no paid API."
Write-Host "Zero publication actions; no real-world semantic accuracy claim."
& $Python -m raglab.evaluation.m2_synth_runner --output-dir "runs/m2-synth01"
if ($LASTEXITCODE -ne 0) { throw "M2_SYNTH01_RUN_FAILED" }
Write-Host "M2_SYNTH01_RESEARCH_CONTROL_COMPLETE"
Write-Host "Read runs/m2-synth01/report.json for per-class measurements."
