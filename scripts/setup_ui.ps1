$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python was not found. Install Python 3.11 or 3.12, then run this script again."
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
}

& ".venv\Scripts\python.exe" -m pip install --upgrade pip
& ".venv\Scripts\python.exe" -m pip install -r requirements-ui-dev.txt
& ".venv\Scripts\python.exe" -m pytest tests/test_claim_review_api.py tests/test_model_registry.py tests/test_openapi_contract.py -q

Write-Host ""
Write-Host "UI environment is ready."
Write-Host "Run: powershell -ExecutionPolicy Bypass -File scripts/run_ui.ps1"
