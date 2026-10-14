"""FastAPI application for the claim-review research prototype."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from src.registry import load_registry

from .schemas import AnalyzeRequest, CaptureSessionRecord, ClaimAnalysis, ClaimIntakeRecord, ClaimIntakeRequest, CorrectionRecord, CorrectionRequest, EvidenceUploadRecord, HealthResponse, MediaAuthenticityReport, ReviewRecord, ReviewRequest
from .service import FixtureClaimService


ROOT = Path(__file__).resolve().parents[2]
MODE = os.getenv("INSURANCE_API_MODE", "fixture")
REGISTRY = load_registry(ROOT / "configs/model_registry.v1.yaml")
if MODE == "fixture":
    SERVICE = FixtureClaimService(ROOT / "prototype/fixtures/claim_analysis_demo.json", ROOT / "runtime/claims")
elif MODE == "live":
    from .live import LiveClaimService

    SERVICE = LiveClaimService(
        ROOT,
        REGISTRY,
        os.getenv("INSURANCE_AUDIT_LOG", str(ROOT / "runtime/audit/reviews.jsonl")),
    )
else:
    raise RuntimeError("INSURANCE_API_MODE must be 'fixture' or 'live'.")

app = FastAPI(
    title="Insurance Claim Review API",
    version=REGISTRY.product_version,
    description="Human-in-the-loop research API. Outputs are decision support, not automatic fraud decisions.",
)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(ROOT / "prototype/claim_review_workbench_v3.html")


@app.get("/workbench.css", include_in_schema=False)
def workbench_css() -> FileResponse:
    return FileResponse(ROOT / "prototype/workbench.css", media_type="text/css")


@app.get("/workbench.js", include_in_schema=False)
def workbench_js() -> FileResponse:
    return FileResponse(ROOT / "prototype/workbench.js", media_type="text/javascript")


@app.get("/intake", include_in_schema=False)
def intake_page() -> FileResponse:
    return FileResponse(ROOT / "prototype/claim_intake.html")


@app.get("/dashboard", include_in_schema=False)
def dashboard_page() -> FileResponse:
    return FileResponse(ROOT / "prototype/admin_dashboard.html")


@app.get("/dashboard.js", include_in_schema=False)
def dashboard_js() -> FileResponse:
    return FileResponse(ROOT / "prototype/dashboard.js", media_type="text/javascript")


@app.get("/api-client.js", include_in_schema=False)
def api_client() -> FileResponse:
    return FileResponse(ROOT / "prototype/api-client.js", media_type="text/javascript")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(mode=MODE, product_version=REGISTRY.product_version)


@app.get("/version")
def version() -> dict:
    return REGISTRY.public_summary()


@app.get("/readiness")
def readiness() -> dict:
    return SERVICE.readiness()


@app.get("/system/model-evidence")
def model_evidence() -> dict:
    training = {
        "tabular_risk": "Nhóm huấn luyện XGBoost trong dự án; có pipeline, hiệu chuẩn và đánh giá khóa.",
        "damage_segmentation": "Nhóm fine-tune YOLOv8s-seg trên CarDD; final test đã khóa.",
        "document_classifier": "Checkpoint DiT pretrained; nhóm đánh giá độc lập, không huấn luyện model này từ đầu.",
        "document_ocr": "PaddleOCR pretrained; nhóm benchmark, không huấn luyện engine này từ đầu.",
        "ocr": "PaddleOCR pretrained; nhóm benchmark, không huấn luyện engine này từ đầu.",
        "document_kie": "Nhóm fine-tune LayoutLMv3 trên split SROIE sạch; final test đã khóa.",
        "consistency_rules": "Luật Python xác định; không có bước huấn luyện.",
        "consistency": "Luật Python xác định; không có bước huấn luyện.",
        "relationships": "Feature NetworkX theo thời điểm; không có bước huấn luyện.",
        "media_authenticity": "Kiểm tra provenance, metadata và reuse chạy local; pixel model chỉ bật sau khi hiệu chuẩn đúng miền.",
    }
    return {
        "processing_location": "local_process",
        "external_llm_api_used": False,
        "claim_data_sent_to_external_llm": False,
        "runtime": SERVICE.readiness(),
        "storage": {
            "claim_files": "runtime/claims/{claim_id}/",
            "analysis": "runtime/claims/{claim_id}/analysis.json",
            "audit_log": "runtime/audit/reviews.jsonl",
            "production_note": "Research storage only; pilot requires authenticated database/object storage and retention policy.",
        },
        "models": {
            name: {
                "implementation": model.implementation, "version": model.version,
                "artifact_hash": model.artifact_hash, "metric": model.primary_metric,
                "metric_value": model.metric_value, "evaluation_split": model.evaluation_split,
                "status": model.status, "training_origin": training.get(name, "See registry/report."),
            }
            for name, model in REGISTRY.modules.items()
        },
    }


@app.get("/claims")
def list_claims() -> list[dict]:
    return SERVICE.list_claims()


@app.post("/claims/{claim_id}/intake", response_model=ClaimIntakeRecord, status_code=201)
def intake(claim_id: str, request: ClaimIntakeRequest) -> ClaimIntakeRecord:
    try:
        return SERVICE.intake(claim_id, request)
    except FileExistsError as error:
        raise HTTPException(
            status_code=409,
            detail="Claim ID đã tồn tại. Hãy tạo mã mới; hệ thống không ghi đè hồ sơ cũ.",
        ) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/claims/{claim_id}/evidence", response_model=EvidenceUploadRecord, status_code=201)
async def upload_evidence(
    claim_id: str,
    kind: str = Form(...),
    capture_session_id: str | None = Form(default=None),
    challenge_step: int | None = Form(default=None),
    file: UploadFile = File(...),
) -> EvidenceUploadRecord:
    try:
        content = await file.read(15 * 1024 * 1024 + 1)
        return SERVICE.upload(
            claim_id, kind, file.filename or "upload", file.content_type, content,
            capture_session_id, challenge_step,
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Create claim intake before uploading evidence.") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/claims/{claim_id}/capture-sessions", response_model=CaptureSessionRecord, status_code=201)
def start_capture_session(claim_id: str) -> CaptureSessionRecord:
    try:
        return SERVICE.start_capture(claim_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Create claim intake before starting guided capture.") from error


@app.get("/claims/{claim_id}/evidence/{evidence_id}/authenticity", response_model=MediaAuthenticityReport)
def evidence_authenticity(claim_id: str, evidence_id: str) -> MediaAuthenticityReport:
    try:
        return SERVICE.authenticity(claim_id, evidence_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Evidence is not available for this claim.") from error
    except (ValueError, OSError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/claims/{claim_id}/evidence/{evidence_id}/content")
def evidence_content(claim_id: str, evidence_id: str) -> FileResponse:
    """Stream one registered evidence file; never accept a filesystem path from the client."""
    try:
        path = SERVICE.runtime_store.evidence_path(claim_id, evidence_id)
        return FileResponse(
            path,
            headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Evidence is not available for this claim.") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/claims/{claim_id}/analyze", response_model=ClaimAnalysis)
def analyze(claim_id: str, request: AnalyzeRequest) -> ClaimAnalysis:
    try:
        return SERVICE.analyze(claim_id, request)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Claim is not available in the configured claim store.") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/claims/{claim_id}/analysis", response_model=ClaimAnalysis)
def analysis(claim_id: str) -> ClaimAnalysis:
    result = SERVICE.get_analysis(claim_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Claim has not been analyzed in this process.")
    return result


@app.get("/claims/{claim_id}/events")
def claim_events(claim_id: str) -> list[dict]:
    try:
        return SERVICE.events(claim_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Claim is not available in the configured claim store.") from error


@app.post("/claims/{claim_id}/review", response_model=ReviewRecord)
def review(claim_id: str, request: ReviewRequest) -> ReviewRecord:
    try:
        return SERVICE.review(claim_id, request)
    except KeyError as error:
        raise HTTPException(status_code=409, detail="Analyze the claim before recording a review.") from error


@app.post("/claims/{claim_id}/corrections", response_model=CorrectionRecord)
def correct(claim_id: str, request: CorrectionRequest) -> CorrectionRecord:
    try:
        return SERVICE.correct(claim_id, request)
    except KeyError as error:
        raise HTTPException(status_code=409, detail="Analyze the claim before recording a correction.") from error
