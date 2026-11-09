$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Raglab = Join-Path $RepoRoot ".venv\Scripts\raglab.exe"
if (-not (Test-Path $Python) -or -not (Test-Path $Raglab)) {
    throw "Local Python environment missing."
}
Write-Host "=== M2 ORIGINAL SCIENTIFIC STANCE: CODE REGRESSIONS ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "PYTEST_FAILED" }

Write-Host "=== M2 EXPERT-LABELLED SCIFACT TRAIN (NO USER PROMPTS) ==="
Write-Host "The original public SciFact source archive may download once; SHA256 pinned."
Write-Host "Evaluating 20 SUPPORT + 20 CONTRADICT rationale pairs with cached NLI model."
& $Raglab evaluate-original-scifact-stances --per-class 20 --seed 17
if ($LASTEXITCODE -ne 0) { throw "ORIGINAL_SCIFACT_STANCE_FAILED" }
Write-Host "M2_ORIGINAL_GOLD_STANCE_EVALUATION_COMPLETE"
Write-Host "Gold labels came from original SciFact TRAIN human annotations."
Write-Host "RAG runtime and TEST split unchanged."
