param(
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Raglab = Join-Path $RepoRoot ".venv\Scripts\raglab.exe"
if (-not (Test-Path $Raglab)) {
    throw "Environment missing. Run .\scripts\setup-local.ps1 first."
}

$latest = Get-ChildItem "runs\v2\answer_*.json" -ErrorAction Stop |
    Sort-Object LastWriteTimeUtc -Descending |
    Select-Object -First 1
if (-not $latest) {
    throw "No saved answer found. Run scripts\run-v2-local.ps1 first."
}

Write-Host "Inspecting existing artifact without regenerating: $($latest.FullName)"
$Arguments = @("inspect-answer", "--path", $latest.FullName, "--with-qrels")
if ($Strict) { $Arguments += "--strict" }

& $Raglab @Arguments
if ($LASTEXITCODE -ne 0) {
    throw "Answer quality gate failed; diagnostic output above explains why."
}
