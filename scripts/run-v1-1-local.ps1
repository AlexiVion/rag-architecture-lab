$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Raglab = Join-Path $RepoRoot ".venv\Scripts\raglab.exe"
if (-not (Test-Path $Raglab)) {
    throw "Local environment not found. Run .\scripts\setup-local.ps1 first."
}

foreach ($CandidateDepth in @(10, 20)) {
    Write-Host "Running matched local comparison: Hybrid RRF vs Hybrid + Cross-Encoder with candidate depth $CandidateDepth..."
    & $Raglab benchmark `
        --dataset beir/scifact/test `
        --pipelines hybrid hybrid-rerank `
        --k 5 10 `
        --rerank-candidates $CandidateDepth
}

Write-Host "V1.1 local ablation complete. Results are in benchmarks/results/."
