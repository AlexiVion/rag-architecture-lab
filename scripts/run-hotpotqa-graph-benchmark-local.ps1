$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Local Python environment missing."
}
Write-Host "=== GRF-00 HOTPOTQA PAIRED STUDY: TESTS ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "PYTEST_FAILED" }

Write-Host "=== OFFICIAL HOTPOTQA DEV DISTRACTOR ==="
Write-Host "The first run downloads about 46 MB to .cache; original SHA256 pinned."
Write-Host "No user prompts, paid APIs, Qwen or model weights."
Write-Host "This is a 60-query bridge-subset BM25 vs Graph+BM25 retrieval study."
& $Python -m raglab.graph.hotpotqa_benchmark --count 60 --seed 17
if ($LASTEXITCODE -ne 0) { throw "GRF00_HOTPOTQA_FAILED" }
Write-Host "GRF00_REAL_DATA_RETRIEVAL_BENCHMARK_COMPLETED"
