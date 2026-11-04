param(
    [switch]$WithGeneration
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Raglab = Join-Path $RepoRoot ".venv\Scripts\raglab.exe"

if (-not (Test-Path $Python) -or -not (Test-Path $Raglab)) {
    Write-Host "Preparing the local Python environment..."
    & (Join-Path $RepoRoot "scripts\setup-local.ps1")
    if ($LASTEXITCODE -ne 0) {
        throw "Local dependency setup failed"
    }
}

Write-Host "=== UNIT TESTS ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) {
    throw "Unit tests failed"
}

Write-Host "=== EXPLORATORY ARCHITECTURE COMPARISON ==="
& $Raglab experiment --spec "experiments/ret-04-parent-child-smoke.json"
if ($LASTEXITCODE -ne 0) {
    throw "Architecture smoke experiment failed"
}

if ($WithGeneration) {
    Write-Host "=== LOCAL V2 GENERATION SMOKE ==="
    & (Join-Path $RepoRoot "scripts\run-v2-local.ps1") -StrictCitations
    if ($LASTEXITCODE -ne 0) {
        throw "V2 generation smoke failed"
    }
}

Write-Host "LOCAL_VERIFICATION_PASS"
Write-Host "Raw experiment outputs: benchmarks/results/ and runs/v2/"
Write-Host "Note: unit/smoke success does NOT certify semantic faithfulness."
Write-Host "Use scripts/inspect-latest-v2-local.ps1 to audit saved generations without running Qwen again."
