$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Raglab = Join-Path $RepoRoot ".venv\Scripts\raglab.exe"
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Raglab) -or -not (Test-Path $Python)) {
    throw "Local environment missing. Run .\scripts\setup-local.ps1 first."
}
Write-Host "=== M2 SEMANTIC REVIEW REGRESSION TESTS ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "PYTEST_FAILED" }

$source = Get-ChildItem "runs\v2\answer_*.json" -ErrorAction Stop |
    Sort-Object LastWriteTimeUtc -Descending |
    Select-Object -First 1
if (-not $source) {
    throw "No local V2 answer artifact was found; do not generate fake answers."
}
$dir = Join-Path $RepoRoot "runs\reviews"
New-Item -ItemType Directory -Path $dir -Force | Out-Null
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$dest = Join-Path $dir ("review_" + $source.BaseName + "_" + $stamp + ".json")
& $Raglab review-export --path $source.FullName --output $dest
if ($LASTEXITCODE -ne 0) { throw "REVIEW_EXPORT_FAILED" }
& $Raglab review-score --path $dest
if ($LASTEXITCODE -ne 0) { throw "REVIEW_SCORE_FAILED" }

Write-Host "M2_REVIEW_PACKET_READY_UNLABELLED"
Write-Host "Review packet: $dest"
Write-Host "No AI model was loaded. Semantic verdicts remain unreviewed."
