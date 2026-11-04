param(
    [string]$Spec = "experiments/ret-04-parent-child-smoke.json"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Raglab = Join-Path $RepoRoot ".venv\Scripts\raglab.exe"
if (-not (Test-Path $Raglab)) {
    throw "Local environment not found. Run .\scripts\setup-local.ps1 first."
}

Write-Host "Running exploratory experiment: $Spec"
& $Raglab experiment --spec $Spec
if ($LASTEXITCODE -ne 0) {
    throw "Experiment failed with exit code $LASTEXITCODE"
}
