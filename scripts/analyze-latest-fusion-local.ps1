$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Raglab = Join-Path $RepoRoot ".venv\Scripts\raglab.exe"
if (-not (Test-Path $Raglab)) {
    throw "Local environment missing. Run .\scripts\setup-local.ps1 first."
}
$latest = Get-ChildItem "benchmarks\results\RET_FUSION_beir_scifact_train_*.json" |
    Where-Object { $_.Name -notmatch "_PAIRED_ANALYSIS" } |
    Sort-Object LastWriteTimeUtc -Descending |
    Select-Object -First 1
if (-not $latest) {
    throw "No saved SciFact training fusion artifact. Run run-fusion-study-local.ps1."
}
Write-Host "Analyzing saved run without embeddings or Qwen: $($latest.FullName)"
& $Raglab analyze-fusion --path $latest.FullName --bootstrap-replicates 2000
if ($LASTEXITCODE -ne 0) {
    throw "Paired analysis failed (exit code $LASTEXITCODE)"
}
Write-Host "PAIRED_FUSION_ANALYSIS_COMPLETED"
