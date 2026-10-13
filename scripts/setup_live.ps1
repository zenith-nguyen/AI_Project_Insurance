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
    New-Item -ItemType Directory -Force -Path (Split-Path $Target) | Out-Null
    if ([string]::IsNullOrWhiteSpace($ArtifactRoot)) {
        $ArtifactUrl = "https://github.com/zenith-nguyen/AI_Project_Insurance/releases/download/research-models-v1/bundle.joblib"
        Write-Host "Downloading registered XGBoost research artifact..."
        Invoke-WebRequest -Uri $ArtifactUrl -OutFile $Target
    } else {
        $Candidates = @(
            (Join-Path $ArtifactRoot "models\tabular_v1\bundle.joblib"),
            (Join-Path $ArtifactRoot "tabular_v1\bundle.joblib"),
            (Join-Path $ArtifactRoot "bundle.joblib")
        )
        $Source = $Candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
        if (-not $Source) {
            throw "bundle.joblib was not found below ArtifactRoot. Checked: $($Candidates -join ', ')"
        }
        Copy-Item -LiteralPath $Source -Destination $Target
    }
}

$Expected = "17649499761df7a6d40d0b0a007d883ec7f3cd68ba9f561af4b169c1d9be28d8"
$Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Target).Hash.ToLower()
if ($Actual -ne $Expected) {
    throw "XGBoost bundle hash mismatch. Expected $Expected, got $Actual"
}

# Optional image model: copied only when the shared artifact root is provided.
$YoloTarget = Join-Path $RepoRoot "artifacts\models\damage_segmentation\cardd_candidate_v1\best.pt"
if (-not [string]::IsNullOrWhiteSpace($ArtifactRoot) -and -not (Test-Path -LiteralPath $YoloTarget)) {
    $YoloCandidates = @(
        (Join-Path $ArtifactRoot "image\cardd_yolov8s_seg_candidate_v1\weights\best.pt"),
        (Join-Path $ArtifactRoot "models\damage_segmentation\cardd_candidate_v1\best.pt"),
        (Join-Path $ArtifactRoot "cardd_yolov8s_seg_candidate_v1\weights\best.pt")
    )
    $YoloSource = $YoloCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if ($YoloSource) {
        New-Item -ItemType Directory -Force -Path (Split-Path $YoloTarget) | Out-Null
        Copy-Item -LiteralPath $YoloSource -Destination $YoloTarget
    } else {
        Write-Warning "YOLO checkpoint was not found. Tabular live mode remains available."
    }
}
if (Test-Path -LiteralPath $YoloTarget) {
    $YoloExpected = "6c0d828760a427d48623653dcd6fffeb1cf591045d9ce8b8684a1d0f5f89420b"
    $YoloActual = (Get-FileHash -Algorithm SHA256 -LiteralPath $YoloTarget).Hash.ToLower()
    if ($YoloActual -ne $YoloExpected) {
        throw "YOLO checkpoint hash mismatch. Expected $YoloExpected, got $YoloActual"
    }
    Write-Host "YOLO checkpoint is registered and ready."
}

$LayoutTarget = Join-Path $RepoRoot "artifacts\models\document_kie\layoutlmv3_sroie_candidate_v2\checkpoint-264"
if (-not [string]::IsNullOrWhiteSpace($ArtifactRoot) -and -not (Test-Path -LiteralPath $LayoutTarget)) {
    $LayoutCandidates = @(
        (Join-Path $ArtifactRoot "document\layoutlmv3_sroie_candidate_v2\checkpoint-264"),
        (Join-Path $ArtifactRoot "models\document_kie\layoutlmv3_sroie_candidate_v2\checkpoint-264"),
        (Join-Path $ArtifactRoot "layoutlmv3_sroie_candidate_v2\checkpoint-264")
    )
    $LayoutSource = $LayoutCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Container } | Select-Object -First 1
    if ($LayoutSource) {
        New-Item -ItemType Directory -Force -Path (Split-Path $LayoutTarget) | Out-Null
        Copy-Item -LiteralPath $LayoutSource -Destination $LayoutTarget -Recurse
    } else {
        Write-Warning "LayoutLMv3 checkpoint was not found. Precomputed document fixtures remain available."
    }
}
if (Test-Path -LiteralPath $LayoutTarget) {
    & ".venv\Scripts\python.exe" scripts\hash_artifact.py $LayoutTarget --expected "2b008c90f764c79be36f7082a96e84ba6d28aaccb512dd801123abe55c1ead3c"
    if ($LASTEXITCODE -ne 0) { throw "LayoutLMv3 checkpoint hash mismatch." }
    Write-Host "LayoutLMv3 checkpoint is registered and ready."
}

& ".venv\Scripts\python.exe" scripts\build_golden_claims.py
& ".venv\Scripts\python.exe" -m pytest tests\test_live_claim_service.py tests\test_claim_review_api.py tests\test_model_registry.py -q

Write-Host ""
Write-Host "Live research environment is ready."
Write-Host "Run: powershell -ExecutionPolicy Bypass -File scripts/run_live.ps1"
