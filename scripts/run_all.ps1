$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $projectRoot
$python = '.\.venv\Scripts\python.exe'
$dvc = '.\.venv\Scripts\dvc.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run .\scripts\setup.ps1 first' }
$env:PATH = (Resolve-Path '.venv\Scripts').Path + ';' + $env:PATH
& $python -m src.data.validate_silver
if ($LASTEXITCODE -ne 0) { throw 'Silver validation failed' }
& $dvc repro
if ($LASTEXITCODE -ne 0) { throw 'DVC reproduction failed' }
& $python -m src.models.train
if ($LASTEXITCODE -ne 0) { throw 'Model training failed' }
& $python -m src.features.robustness_audit
if ($LASTEXITCODE -ne 0) { throw 'Robustness audit failed' }
& $python -m src.explainability.shap_analysis
if ($LASTEXITCODE -ne 0) { throw 'Explanation export failed' }
& $python -m src.evaluation.report
if ($LASTEXITCODE -ne 0) { throw 'Report generation failed' }
& $python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
Write-Host 'Pipeline complete: reports/RESULTS.md'
