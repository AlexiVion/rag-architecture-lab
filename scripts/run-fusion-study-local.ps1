param(
    [int]$LimitQueries = 0
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Raglab = Join-Path $RepoRoot ".venv\Scripts\raglab.exe"
if (-not (Test-Path $Raglab)) {
    throw "Local environment missing. Run .\scripts\setup-local.ps1 first."
}
$Arguments = @(
    "fusion-study",
    "--dataset", "beir/scifact/train",
    "--weights", "1.5", "2", "3",
    "--k", "5", "10",
    "--candidate-k", "100"
)
if ($LimitQueries -gt 0) {
    $Arguments += @("--limit-queries", "$LimitQueries")
}
Write-Host "Comparing BM25 / Dense / RRF / weighted RRF on SciFact TRAIN only."
Write-Host "One local embedding index is reused; no Qwen is called."
& $Raglab @Arguments
if ($LASTEXITCODE -ne 0) {
    throw "Fusion training study failed (exit code $LASTEXITCODE)"
}
Write-Host "FUSION_STUDY_TRAIN_COMPLETED"
