$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Raglab = Join-Path $RepoRoot ".venv\Scripts\raglab.exe"
if (-not (Test-Path $Raglab)) {
    throw "Local environment not found. Run .\scripts\setup-local.ps1 first."
}

Write-Host "Running V1 locally: Hybrid RRF vs Hybrid + Cross-Encoder reranking..."
& $Raglab benchmark `
    --dataset beir/scifact/test `
    --pipelines hybrid hybrid-rerank `
    --k 5 10 `
    --rerank-candidates 50

Write-Host "V1 local benchmark complete. Results are in benchmarks/results/."
