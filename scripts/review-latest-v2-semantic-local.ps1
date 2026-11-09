$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Raglab = Join-Path $RepoRoot ".venv\Scripts\raglab.exe"
if (-not (Test-Path $Raglab)) {
    throw "Local environment missing. Run .\scripts\setup-local.ps1 first."
}
$packet = Get-ChildItem "runs\reviews\review_answer_*.json" -ErrorAction Stop |
    Sort-Object LastWriteTimeUtc -Descending |
    Select-Object -First 1
if (-not $packet) {
    throw "No original review packet found. Run prepare-v2-semantic-review-local.ps1 first."
}
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$dest = Join-Path $packet.DirectoryName ("annotated_" + $packet.BaseName + "_" + $stamp + ".json")

Write-Host "Human review of original packet: $($packet.FullName)"
Write-Host "A new file will be written; the original packet will not change."
Write-Host "The console will ask for 5 source relevance labels and 1 claim support verdict."
& $Raglab review-interactive --path $packet.FullName --output $dest
if ($LASTEXITCODE -ne 0) {
    throw "Human review command failed (exit code $LASTEXITCODE)"
}
Write-Host "M2_HUMAN_REVIEW_SESSION_FINISHED"
Write-Host "Annotated packet: $dest"
