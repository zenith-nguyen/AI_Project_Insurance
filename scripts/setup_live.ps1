param(
    [string]$ArtifactRoot = ""
)

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
& ".venv\Scripts\python.exe" -m pip install -r requirements-live.txt

$Target = Join-Path $RepoRoot "artifacts\models\tabular_v1\bundle.joblib"
if (-not (Test-Path -LiteralPath $Target)) {
    if ([string]::IsNullOrWhiteSpace($ArtifactRoot)) {
        throw "Missing XGBoost bundle. Re-run with -ArtifactRoot pointing to the shared artifact folder."
    }
    $Candidates = @(
        (Join-Path $ArtifactRoot "models\tabular_v1\bundle.joblib"),
        (Join-Path $ArtifactRoot "tabular_v1\bundle.joblib"),
        (Join-Path $ArtifactRoot "bundle.joblib")
    )
    $Source = $Candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $Source) {
        throw "bundle.joblib was not found below ArtifactRoot. Checked: $($Candidates -join ', ')"
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $Target) | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Target
}

$Expected = "17649499761df7a6d40d0b0a007d883ec7f3cd68ba9f561af4b169c1d9be28d8"
$Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Target).Hash.ToLower()
if ($Actual -ne $Expected) {
    throw "XGBoost bundle hash mismatch. Expected $Expected, got $Actual"
}

& ".venv\Scripts\python.exe" scripts\build_golden_claims.py
& ".venv\Scripts\python.exe" -m pytest tests\test_live_claim_service.py tests\test_claim_review_api.py tests\test_model_registry.py -q

Write-Host ""
Write-Host "Live research environment is ready."
Write-Host "Run: powershell -ExecutionPolicy Bypass -File scripts/run_live.ps1"
