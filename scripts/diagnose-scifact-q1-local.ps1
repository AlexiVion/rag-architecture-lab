param(
    [switch]$BM25Only
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Raglab = Join-Path $RepoRoot ".venv\Scripts\raglab.exe"

if (-not (Test-Path $Raglab)) {
    throw "Local environment missing. Run .\scripts\setup-local.ps1 first."
}

$Methods = if ($BM25Only) { @("bm25") } else { @("bm25", "dense", "hybrid") }
$Arguments = @(
    "diagnose-retrieval",
    "--dataset", "beir/scifact/test",
    "--query-id", "1",
    "--strategies"
) + $Methods + @(
    "--candidate-k", "100",
    "--context-k", "5"
)

Write-Host "=== SCIFACT QUERY 1 RETRIEVAL DIAGNOSIS ==="
Write-Host "Offline labels, WITHOUT Qwen and WITHOUT cross-encoder."
& $Raglab @Arguments
if ($LASTEXITCODE -ne 0) {
    throw "Retrieval diagnosis failed (exit code $LASTEXITCODE)"
}
Write-Host "RETRIEVAL_DIAGNOSIS_COMPLETED"
