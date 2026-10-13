"""FastAPI application for the claim-review research prototype."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from src.registry import load_registry

from .schemas import AnalyzeRequest, ClaimAnalysis, ClaimIntakeRecord, ClaimIntakeRequest, CorrectionRecord, CorrectionRequest, EvidenceUploadRecord, HealthResponse, MediaAuthenticityReport, ReviewRecord, ReviewRequest
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
    return FileResponse(ROOT / "prototype/insurance_review_console_v2.html")


@app.get("/intake", include_in_schema=False)
def intake_page() -> FileResponse:
    return FileResponse(ROOT / "prototype/claim_intake.html")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(mode=MODE, product_version=REGISTRY.product_version)


@app.get("/version")
def version() -> dict:
    return REGISTRY.public_summary()


@app.post("/claims/{claim_id}/intake", response_model=ClaimIntakeRecord, status_code=201)
def intake(claim_id: str, request: ClaimIntakeRequest) -> ClaimIntakeRecord:
    try:
        return SERVICE.intake(claim_id, request)
    except FileExistsError as error:
        raise HTTPException(status_code=409, detail="claim_id already exists in the runtime claim store.") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/claims/{claim_id}/evidence", response_model=EvidenceUploadRecord, status_code=201)
async def upload_evidence(
    claim_id: str,
    kind: str = Form(...),
    file: UploadFile = File(...),
) -> EvidenceUploadRecord:
    try:
        content = await file.read(15 * 1024 * 1024 + 1)
        return SERVICE.upload(claim_id, kind, file.filename or "upload", file.content_type, content)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Create claim intake before uploading evidence.") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/claims/{claim_id}/evidence/{evidence_id}/authenticity", response_model=MediaAuthenticityReport)
def evidence_authenticity(claim_id: str, evidence_id: str) -> MediaAuthenticityReport:
    try:
        return SERVICE.authenticity(claim_id, evidence_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Evidence is not available for this claim.") from error
    except (ValueError, OSError) as error:
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
