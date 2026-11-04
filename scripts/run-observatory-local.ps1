param(
    [switch]$NoServe,
    [int]$Port = 4188
)
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Local virtual environment missing. Run .\scripts\setup-local.ps1 first."
}

Write-Host "=== GRF-00 DETERMINISTIC EVIDENCE GRAPH ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "GRAPH_TESTS_FAILED" }

Write-Host "=== VALIDATING + GENERATING PUBLIC OFFLINE FIXTURE ==="
& $Python -m raglab.observatory.fixture --output "apps/explorer/data/demo.json"
if ($LASTEXITCODE -ne 0) { throw "GRAPH_FIXTURE_EXPORT_FAILED" }

Write-Host "GRF00_TWO_HOP_FIXTURE_PASS"
if ($NoServe) { return }

if ($Port -lt 1024 -or $Port -gt 65535) {
    throw "Choose a user-space TCP port between 1024 and 65535"
}
$URL = "http://127.0.0.1:$Port/"
Write-Host "Graph observatory (offline illustrative fixture): $URL"
Write-Host "Use Ctrl+C to stop the local server."
Start-Process $URL
& $Python -m http.server $Port --bind 127.0.0.1 --directory "apps/explorer"
