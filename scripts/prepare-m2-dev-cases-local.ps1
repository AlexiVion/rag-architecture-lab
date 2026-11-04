$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Raglab = Join-Path $RepoRoot ".venv\Scripts\raglab.exe"
if (-not (Test-Path $Raglab) -or -not (Test-Path $Python)) {
    throw "Local virtual environment is missing."
}

Write-Host "=== M2 DEV DATASET: TESTS ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "PYTEST_FAILED" }

$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssfffffffZ")
$dir = Join-Path $RepoRoot ("runs\dev-cases\M2-DEV-EVIDENCE-01_" + $stamp)
Write-Host "Building TRAIN-only unlabelled review cases: $dir"
& $Raglab design-dev-cases --dataset "beir/scifact/train" --query-count 6 --seed 17 --output-dir $dir
if ($LASTEXITCODE -ne 0) { throw "DEV_CASE_DESIGN_FAILED" }
Write-Host "M2_DEV_CASES_UNLABELLED_READY"
Write-Host "Manifest: $(Join-Path $dir 'manifest.json')"
Write-Host "Packets: $dir"
Write-Host "NO Qwen, cross-encoder or embeddings were run."
