$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Missing .venv. Run scripts/setup_live.ps1 first."
}

$env:INSURANCE_API_MODE = "live"
$YoloWeights = Join-Path $RepoRoot "artifacts\models\damage_segmentation\cardd_candidate_v1\best.pt"
if (Test-Path -LiteralPath $YoloWeights) {
    & ".venv\Scripts\python.exe" -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('ultralytics') else 1)"
    if ($LASTEXITCODE -eq 0) {
        $env:INSURANCE_YOLO_WEIGHTS = $YoloWeights
    } else {
        Write-Warning "YOLO checkpoint exists but ultralytics is not installed. Install requirements-gpu.txt to enable image inference."
    }
}
$LayoutCheckpoint = Join-Path $RepoRoot "artifacts\models\document_kie\layoutlmv3_sroie_candidate_v2\checkpoint-264"
if (Test-Path -LiteralPath $LayoutCheckpoint) {
    & ".venv\Scripts\python.exe" -c "import importlib.util,sys; names=('torch','transformers','paddle','paddleocr','pypdfium2'); sys.exit(0 if all(importlib.util.find_spec(name) for name in names) else 1)"
    if ($LASTEXITCODE -eq 0) {
        $env:INSURANCE_LAYOUTLM_CHECKPOINT = $LayoutCheckpoint
    } else {
        Write-Warning "LayoutLMv3 checkpoint exists but document dependencies are incomplete. Install requirements-document.txt and PaddlePaddle."
    }
}
& ".venv\Scripts\python.exe" -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload
