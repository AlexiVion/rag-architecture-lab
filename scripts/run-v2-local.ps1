param(
    [string]$Query = "",
    [switch]$Quality
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Raglab = Join-Path $RepoRoot ".venv\Scripts\raglab.exe"
if (-not (Test-Path $Raglab)) {
    throw "Local environment not found. Run .\scripts\setup-local.ps1 first."
}

$Pipeline = if ($Quality) { "hybrid-rerank" } else { "hybrid" }

$Arguments = @(
    "answer",
    "--dataset", "beir/scifact/test",
    "--pipeline", $Pipeline,
    "--top-k", "5",
    "--rerank-candidates", "10",
    "--model", "Qwen/Qwen2.5-0.5B-Instruct",
    "--max-new-tokens", "180"
)

if ($Query) {
    $Arguments += @("--query", $Query)
}

Write-Host "Running V2 locally with pipeline: $Pipeline"
& $Raglab @Arguments
