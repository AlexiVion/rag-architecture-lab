$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    py -3.11 -m venv .venv
}

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

Write-Host "Upgrading pip..."
& $Python -m pip install --upgrade pip

Write-Host "Installing benchmark, generation, and development dependencies..."
& $Python -m pip install -e ".[benchmark,generation,dev]"

Write-Host "Running unit tests..."
& $Python -m pytest

Write-Host "Local environment ready."
