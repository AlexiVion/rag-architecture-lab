$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Raglab = Join-Path $RepoRoot ".venv\Scripts\raglab.exe"
if (-not (Test-Path $Raglab)) {
    throw "Local environment missing. Run .\scripts\setup-local.ps1 first."
}
$latest = Get-ChildItem "benchmarks\results\beir_scifact_train_*.json" |
    Where-Object { $_.Name -notmatch "_ANALYSIS" } |
    Sort-Object LastWriteTimeUtc -Descending |
    Select-Object -First 1
if (-not $latest) {
    throw "No saved SciFact train benchmark JSON. Run rerank-depth20 smoke first."
}
Write-Host "Analyzing saved benchmark: $($latest.FullName)"
Write-Host "NO Qwen or cross-encoder invoked."
& $Raglab analyze-rerank --path $latest.FullName
if ($LASTEXITCODE -ne 0) {
    throw "Rerank paired analysis failed (exit code $LASTEXITCODE)"
}
Write-Host "PAIRED_RERANK_ANALYSIS_COMPLETED"
