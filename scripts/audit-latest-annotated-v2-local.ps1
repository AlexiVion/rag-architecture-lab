$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Raglab = Join-Path $RepoRoot ".venv\Scripts\raglab.exe"
if (-not (Test-Path $Raglab)) { throw "Local environment missing." }

$review = Get-ChildItem "runs\reviews\annotated_*.json" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTimeUtc -Descending |
    Select-Object -First 1
if (-not $review) {
    throw "No annotated review available. Finish the human review first."
}
$dest = Join-Path $review.DirectoryName ("summary_" + $review.BaseName + ".json")
if (Test-Path $dest) {
    throw "The summary already exists: $dest. The original result will not be overwritten."
}
Write-Host "=== M2 INDEPENDENT DIMENSIONS ==="
Write-Host "Human review: $($review.FullName)"
& $Raglab review-score --path $review.FullName --output $dest
if ($LASTEXITCODE -ne 0) { throw "REVIEW_SCORE_FAILED" }
Write-Host "M2_REVIEW_SUMMARY_SAVED"
Write-Host "The human review JSON was not changed; no models were invoked."
