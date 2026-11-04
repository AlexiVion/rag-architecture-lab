param(
    [int]$LimitQueries = 60
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Raglab = Join-Path $RepoRoot ".venv\Scripts\raglab.exe"
if (-not (Test-Path $Raglab)) {
    throw "Local environment missing. Run .\scripts\setup-local.ps1 first."
}
if ($LimitQueries -le 0) {
    throw "LimitQueries must be positive; expand only after reviewing the smoke results."
}

Write-Host "=== RET-RERANK-20: DEVELOPMENT SMOKE ==="
Write-Host "Dataset: beir/scifact/train | Queries: $LimitQueries"
Write-Host "Baseline: hybrid | Candidate: hybrid-rerank, pool=20"
Write-Host "Local cross-encoder + embeddings, NO Qwen generation."

& $Raglab benchmark --dataset "beir/scifact/train" `
    --pipelines hybrid hybrid-rerank `
    --k 5 10 `
    --rerank-candidates 20 `
    --limit-queries $LimitQueries

if ($LASTEXITCODE -ne 0) {
    throw "Reranking smoke benchmark failed (exit code $LASTEXITCODE)"
}
Write-Host "RERANK_DEPTH20_SMOKE_COMPLETED"
Write-Host "Results stored locally under benchmarks/results/"
