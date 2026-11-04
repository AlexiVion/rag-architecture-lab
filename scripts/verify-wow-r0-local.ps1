$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Missing local .venv. See docs/RELEASE_INSTALLATION.md." }
Write-Host "=== WOW R0: FULL PYTHON TEST SUITE (NO MODEL GENERATION) ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "R0_FULL_TESTS_FAILED" }
Write-Host "=== WOW R0: CHECK DISTRIBUTABLE SOURCES AND PUBLIC ARTIFACTS ==="
& $Python -m raglab.release_readiness --json-output "runs/release-r0/engineering.json"
if ($LASTEXITCODE -ne 0) { throw "R0_SOURCE_INTEGRITY_FAILED" }
Write-Host "=== WOW R0: INSTALLED CLI ==="
& $Python -m raglab.cli --help
if ($LASTEXITCODE -ne 0) { throw "R0_CLI_FAILED" }
Write-Host "=== WOW R0: NO-DEPENDENCY PYTHON WHEEL BUILD ==="
& $Python -m pip wheel --no-deps --wheel-dir "runs/release-r0/wheels" .
if ($LASTEXITCODE -ne 0) { throw "R0_WHEEL_BUILD_FAILED" }
Write-Host "WOW_R0_LOCAL_ENGINEERING_CHECK_PASS"
Write-Host "Not a scientific M2 or full WOW v1.0 release certificate."

