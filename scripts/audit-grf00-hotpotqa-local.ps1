$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Local Python environment missing." }

Write-Host "=== GRF-00 POST-RUN AUDIT: FULL TEST SUITE ==="
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "GRF00_AUDIT_TESTS_FAILED" }

$source = Get-ChildItem "runs\graph-hotpotqa\GRF00_HOTPOTQA_*.json" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTimeUtc -Descending |
    Select-Object -First 1
if (-not $source) { throw "No local HotpotQA benchmark result found." }

$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssfffffffZ")
$markdown = Join-Path $source.DirectoryName ("GRF00_AUDITED_" + $stamp + ".md")
$webfile = Join-Path $RepoRoot "apps\explorer\data\hotpotqa-summary.local.json"

Write-Host "=== VERIFY ORIGINAL 60-QUERY REPORT ==="
Write-Host "Source: $($source.FullName)"
& $Python -m raglab.graph.hotpotqa_diagnosis --input $source.FullName --markdown-output $markdown --web-output $webfile
if ($LASTEXITCODE -ne 0) { throw "GRF00_AUDIT_FAILED" }

Write-Host "GRF00_POSTRUN_AUDIT_COMPLETE"
Write-Host "Existing viewer: http://127.0.0.1:4874/"
Write-Host "Refresh to view the verified local research summary."
Write-Host "No new benchmark run, generator or paid API."
