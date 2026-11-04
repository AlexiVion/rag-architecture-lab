$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Raglab = Join-Path $RepoRoot ".venv\Scripts\raglab.exe"
if (-not (Test-Path $Python) -or -not (Test-Path $Raglab)) {
    throw "Local environment not found. Run scripts\setup-local.ps1 first."
}
Write-Host "=== V2 OUTPUT SAFETY REGRESSIONS ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "PYTEST_FAILED" }

$historical = Get-ChildItem "runs\v2\answer_*.json" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTimeUtc -Descending |
    Select-Object -First 1
if ($historical) {
    Write-Host "=== HISTORICAL ANSWER AUDIT (NO GENERATION) ==="
    & $Raglab inspect-answer --path $historical.FullName
    if ($LASTEXITCODE -ne 0) { throw "HISTORICAL_AUDIT_FAILED" }
}
Write-Host "V2_OUTPUT_GATE_LOCAL_TESTS_PASS"
Write-Host "Note: offline and fake-generator checks do NOT certify semantic faithfulness."
