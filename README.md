# Motor insurance claim fraud risk research

This repository reproduces a **tabular research baseline** for the UEH CPMAI project. It scores claims for human review; a score is not evidence of fraud and must never automatically reject a claim. CarDD images and CORD documents are separate, unlinked sources and are not fused with the Kaggle rows.

Team-ready handoff documents for Progress Report 2 are indexed in `reports/handoff/README.md`.

## One-command handoff (Windows/macOS)

The shortest supported handoff path is the fixture Docker application. It needs no raw data, checkpoint or GPU:

```bash
python scripts/handoff.py up
```

Use `python3` on macOS when `python` is not available. The command runs preflight, starts `compose.yaml`, waits for health and smoke-tests the UI/API. Start with `docs/final_handoff/00_START_HERE.md`; model/API integration and macOS risks are kept in the same three-file handoff set.

The API lifecycle, UI/backend responsibilities, guided-capture example and error-handling rules are documented in `reports/API_HANDOFF_GUIDE_2026-10-13.md`. Browser clients can import `prototype/api-client.js` instead of duplicating raw `fetch` calls.

The numbered handoff handbook starts at `docs/handbook/00_START_HERE.md`. Build a PDF + ZIP draft with `python scripts/build_handoff_bundle.py --status draft`; final packaging is deliberately gated by the release/UAT checklist.

Project completion is versioned in `configs/project_definition_of_done_v1.yaml`. Run `python scripts/check_project_done.py --output runtime/project_done.json --no-fail` to see the exact remaining blockers; a `FINAL` bundle cannot be produced until the `research_handoff` target passes.

## Claim Review API and prototype

The repository now includes a fixture-first FastAPI contract and reviewer prototype. This lets the UI team integrate before live model adapters are released.

For the UI team, the recommended setup is Docker Desktop:

```powershell
docker compose up --build
```

This starts the fixture workbench and API without raw data, Google Drive, GPU, or model checkpoints. Open `http://127.0.0.1:8000/` for the workbench and `http://127.0.0.1:8000/docs` for Swagger. The complete two-role onboarding and artifact procedure is in `reports/TEAM_ONBOARDING_AND_ARTIFACT_SETUP_2026-10-13.md`.

Without Docker, use:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_ui.ps1
powershell -ExecutionPolicy Bypass -File scripts/run_ui.ps1
```

The Docker/UI default intentionally starts in `fixture` mode. Live adapters remain gated by registry entries, hashes, schemas and validation evidence. See `reports/PRODUCT_HANDOFF_AND_METRIC_PLAN_2026-10-12.md` for the product, metric and transfer plan.

The first local live slice is also available for ML/backend integration. It runs the registered XGBoost bundle, consistency rules and point-in-time NetworkX graph against five de-identified golden claims. OCR, KIE and damage inference remain explicitly inactive in this slice. If the bundle already exists in this workspace:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_live.ps1
powershell -ExecutionPolicy Bypass -File scripts/run_live.ps1
```

On a fresh clone, `setup_live.ps1` downloads the pinned research bundle from the repository's `research-models-v1` GitHub Release and verifies its SHA-256. A local shared artifact directory can be used instead:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_live.ps1 -ArtifactRoot "D:\shared-model-artifacts"
```

On the ML/backend integration machine, add `-InstallMultimodalDependencies` to install the optional YOLO and document runtimes when their registered checkpoints are present. Setup also analyzes all five golden claims through the live API and writes `runtime/core_live_smoke.json`; run `scripts/run_golden_live_smoke.py --require-all` when closing the multimodal handoff gate.

Open the single product entry point at `http://127.0.0.1:8000/`. It starts at the operations dashboard; use the in-app menu for intake, workbench and audit history. Swagger remains a developer-only view at `http://127.0.0.1:8000/docs`. Reviews and field corrections are persisted under `runtime/audit/`; uploaded claim evidence stays under `runtime/claims/`. Both remain outside Git. The dashboard explains the XGBoost queue score, input completeness and review flags separately, and links each claim to its saved audit history.

Uploaded images automatically pass through `media_authenticity_v3`: built-in EXIF/XMP and descriptive pixel features always run, while ExifTool and signed C2PA Content Credentials checks activate when their command-line tools are installed. The module reports declared AI and editing-software markers separately. Runtime uploads receive rotation and center-crop perceptual hashes and are compared with images from other claims to flag exact or recompressed/resized reuse. The claim analysis includes the cached result automatically. `GET /claims/{claim_id}/evidence/{evidence_id}/authenticity` is only an audit/debug view of that same automatic result. A missing marker is reported as inconclusive, never as proof that an image is genuine; see `reports/MEDIA_AUTHENTICITY_AND_RELATIONSHIP_MATCHING_V3_2026-10-14.md`.

Live analysis is tolerant of missing modalities. If the required tabular fields are present, XGBoost can still return a research priority score when documents, vehicle images, or relationship data are missing. The response is marked `analysis_status: partial`, and every module reports `completed`, `skipped_missing_input`, `unavailable`, or `blocked_missing_input`. Missing relationship data is never represented as zero relationships. If required tabular model features are missing, the response is `blocked` and has no risk score while other available evidence checks may still run.

The intake UI also supports a 10-minute guided-capture session. `POST /claims/{claim_id}/capture-sessions` returns three ordered instructions, including a random angle prompt. Each uploaded image is bound to a session and step, duplicate steps are rejected, and the analysis exposes whether all three steps were received. This is recorded as `guided_unverified`: it raises collection assurance but does not cryptographically prove that the pixels were captured live.

The live orchestrator also activates the real YOLO adapter when `INSURANCE_YOLO_WEIGHTS` points to the registered checkpoint, and the DiT → PaddleOCR → LayoutLMv3 adapter when `INSURANCE_LAYOUTLM_CHECKPOINT` points to the registered checkpoint directory. Both adapters verify artifact hashes before loading. `scripts/setup_live.ps1 -ArtifactRoot <shared-artifacts>` copies and verifies available artifacts; `scripts/run_live.ps1` enables only modules whose dependencies are installed.

## Current data and scope

The tabular source is Kaggle `arpan129/insurance-fraud-detection`, workbook `Worksheet in Case Study question 2.xlsx`, sheet `Fraud_Detection_decsion tree`. Bronze retains the workbook and a hash manifest. Silver normalizes names/missing values and adds trace IDs. Gold `dataset_v2` freezes a stratified 70/10/20 split with exact integer counts. DVC tracks Bronze/Silver and generates Gold. Raw files and model artifacts remain outside Git; no DVC remote is configured.

The source has 1,000 records, 247 labeled fraud. Those labels and the timing of several fields need domain validation before any operational use. The 24.7% source prevalence is far above the proposed 5–10% business scenarios. Scenario estimates assume stable score distributions within each class; they are not external validation.

## Local setup (PowerShell)

From this prepared workspace, `powershell -ExecutionPolicy Bypass -File scripts/run_all.ps1` validates and reruns the entire tabular pipeline. The scripts below show individual steps for a fresh checkout.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If script execution is disabled, use `.\.venv\Scripts\python.exe` directly and prepend `.venv\Scripts` to `PATH` before `dvc repro`.

To recover source data from Kaggle in a new checkout, download `arpan129/insurance-fraud-detection` with KaggleHub or Kaggle CLI, place the named workbook under `data/bronze/layerB_claims/`, then run:

```powershell
python -m src.data.ingest_claims 'data/bronze/layerB_claims/Worksheet in Case Study question 2.xlsx'
python -m src.data.validate_silver
dvc repro
python -m src.models.train
python -m src.features.robustness_audit
python -m src.features.feature_policy_validation
python -m src.explainability.shap_analysis
python -m src.models.predict data/gold/dataset_v2/test.parquet reports/metrics/test_queue.csv
pytest -q
```

The ingest command refuses to overwrite Silver v1. If the user's original Colab Silver files are available, put `claims_silver_v1.parquet` and `manifest_v1.json` in `data/silver/layerB_claims/`, then run validation before Gold. Their hashes may differ from the locally reconstructed Silver because Parquet serialization can differ.

## Evaluation protocol

The original baseline used train for feature audit/model selection and validation for queue thresholds, then scored the 200-row test. That same test was later reused once for the bias-exclusion sensitivity check. As of 2026-10-05 it is spent for feature-policy comparison. DVC now derives `train_fs` (560 rows) and `val_fs` (140 rows) strictly from the original 700-row train; all further feature-selection decisions use these splits. After the feature policy and model are frozen, final performance requires a new external test. Fixed top-K ties use stable row order. Production-prevalence scenarios remain label-shift simulations, not external validation.

The feature policy in `configs/features.yaml` conservatively excludes IDs, location proxies, raw dates, the source target, and potentially redundant totals. Fields in `review_before_use` require confirmation that they are known at scoring time. `reports/leakage/` contains a train-only descriptive audit; association is not proof of leakage. `configs/rules.yaml` holds the baseline heuristics, including a claim amount quantile fitted only on train.

`reports/RESULTS.md` is the readable result; `reports/metrics/tabular_v1.json` contains detailed numbers. `reports/metrics/test_predictions.csv` provides claim-level scores and labels for local analysis. These files and `artifacts/` are ignored by Git. Business net value is intentionally unavailable until `configs/business.yaml` contains real costs and avoided losses.

`configs/features.yaml` contains `EXCLUDE_BIASED_FEATURES`. When enabled, training drops `insured_hobbies`, `insured_zip`, and `incident_location`, and writes a separate `tabular_bias_excluded_v1` result/artifact without overwriting the original baseline.

Run `python -m src.features.feature_policy_validation` to compare current candidate policies on `val_fs` without reading the spent test. Results are written to `reports/FEATURE_POLICY.md` and `reports/metrics/feature_policy_val_fs_v1.json`.

CarDD exists only in Google Drive/Colab. After mounting Drive in Colab, inspect its FiftyOne folder before conversion or training:

```python
!python scripts/inspect_cardd.py "/content/drive/MyDrive/AI_Project_Insurance/data/bronze/layerA_cardd"
```

The inspector reads `fiftyone.yml`, `samples.json`, `metadata.json`, counts images under `data/`, discovers annotation classes and geometry actually present, and extracts `CarDD_license.pdf`. It does not assume COCO annotations.

`configs/stages.yaml` defines candidate feature sets for intake and complete-file scoring checkpoints. Stage-model training remains excluded from `run_all.ps1` until the business team confirms which fields exist at each moment. `reports/ROBUSTNESS.md` contains the train-only sensitivity check.

## Image branch

`src/image/train_yolo.py` accepts a real Ultralytics segmentation `data.yaml` and runs separately on GPU. CarDD mirror metadata must be inspected and converted with its actual labels; the image branch has no claim-level linkage to the tabular data. Install `requirements-gpu.txt` in a separate Colab/GPU environment. Do not redistribute restricted raw images.

Google Drive should retain one copy of the CarDD images under Bronze. The converter now defaults to `--image-mode labels-only`; existing converted outputs that contain copied images can be reduced with `scripts/slim_cardd_yolo_storage.py`. Before validation or training, `scripts/materialize_cardd_training_view.py` creates an ephemeral `/content/cardd_yolo_v1` view whose image and label entries are symbolic links. This keeps the split and labels reproducible without storing the 2,816 images twice on Drive.

```python
!python scripts/materialize_cardd_training_view.py \
  "/content/drive/MyDrive/AI_Project_Insurance/data/bronze/layerA_cardd" \
  "/content/drive/MyDrive/AI_Project_Insurance/data/processed/cardd_yolo_v1" \
  "/content/cardd_yolo_v1"
```

CarDD training and evaluation are complete. YOLOv8s-seg was selected on validation and evaluated exactly once on 419 test images/931 instances; final-test mask mAP50-95 is `0.513978`. The report and execution lock passed the read-only integrity checks. Do not rerun or tune against the final test. The exact protocol and metrics are documented in `reports/CARDD_MODEL_SELECTION_V1.md` and `reports/CARDD_TRAINING_PLAN.md`.

## Document branch

Use `notebooks/Document_Data_Intake_Acc2_v1.ipynb` on a CPU Colab runtime to register and download document datasets into `data/bronze/documents/<source>/<version>`. The notebook pins CORD, downloads the official FUNSD archive and XFUND release, supports an RRC archive or a version-pinned Kaggle mirror for SROIE, inventories MIDV Zenodo records, and gates large MIDV/RVL-CDIP downloads by free space. It writes one source manifest per dataset plus `data/registry/documents/document_sources_registry.json`.

The operating rules are in `reports/DOCUMENT_DATA_OPERATIONS_GUIDE_V1.md`; source/license findings are in `reports/DOCUMENT_SOURCE_LINK_AUDIT_V1.md`. Public document datasets remain separate from claims and CarDD. Only real operational documents with a valid `claim_id` may be integrated according to `reports/DOCUMENT_CLAIM_INTEGRATION_CONTRACT_V1.md`.

## Important limits

This is an academic baseline, not a deployed claims decision system. The test has roughly 49 positive cases, so results have wide uncertainty. There is no prospective validation, linked multimodal dataset, verified production prevalence, measured review costs, or operational approval for automatic processing.
