"""Stable request and response schemas shared with prototype clients."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class AnalyzeRequest(BaseModel):
    claim_amount: float | None = Field(default=None, ge=0)
    incident_date: str | None = None
    plate_number: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class ClaimIntakeRequest(BaseModel):
    claim_amount: float | None = Field(default=None, ge=0)
    incident_date: str | None = None
    plate_number: str | None = None
    scored_at: str | None = None
    tabular_features: dict[str, Any] = Field(default_factory=dict)
    required_evidence: list[str] = Field(default_factory=lambda: ["claim-intake", "vehicle_image", "claim_document"])


class ClaimIntakeRecord(BaseModel):
    claim_id: str
    created_at: str
    status: Literal["stored"] = "stored"


class CaptureInstruction(BaseModel):
    step: int = Field(ge=1)
    instruction: str


class CaptureSessionRecord(BaseModel):
    claim_id: str
    session_id: str
    created_at: str
    expires_at: str
    status: Literal["issued", "completed", "expired"]
    instructions: list[CaptureInstruction]
    submissions: dict[str, str] = Field(default_factory=dict)
    assurance_level: Literal["guided_unverified"] = "guided_unverified"


class EvidenceUploadRecord(BaseModel):
    claim_id: str
    evidence_id: str
    kind: Literal["image", "document"]
    original_filename: str
    stored_uri: str
    content_type: str | None = None
    size_bytes: int = Field(gt=0)
    sha256: str
    perceptual_hash: str | None = None
    color_signature: list[int] | None = None
    capture_session_id: str | None = None
    challenge_step: int | None = None
    capture_assurance: Literal["guided_unverified"] | None = None
    observed_at: str
    authenticity_verdict: Literal["ai_provenance_detected", "provenance_problem", "review", "inconclusive", "error"] | None = None


class AuthenticityFinding(BaseModel):
    code: str
    source: Literal["metadata", "exiftool", "c2pa", "synthid", "forensic_model", "cross_claim"]
    outcome: Literal["detected", "absent", "completed", "unavailable", "error"]
    severity: Literal["info", "review", "high"]
    explanation: str
    confidence: float | None = Field(default=None, ge=0, le=1)


class MediaAuthenticityReport(BaseModel):
    schema_version: str = "1.0"
    evidence_id: str | None = None
    analyzer_version: str
    sha256: str
    verdict: Literal["ai_provenance_detected", "provenance_problem", "review", "inconclusive"]
    human_review_required: bool
    findings: list[AuthenticityFinding] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    image_info: dict[str, Any] = Field(default_factory=dict)
    c2pa_manifest: dict[str, Any] | None = None
    limitations: list[str] = Field(default_factory=list)


class Evidence(BaseModel):
    evidence_id: str
    kind: Literal["claim", "image", "document", "relationship"]
    label: str
    source_uri: str | None = None
    observed_at: str | None = None
    content_type: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    sha256: str | None = None


class Signal(BaseModel):
    signal_id: str
    category: Literal["risk", "damage", "document", "consistency", "relationship", "authenticity"]
    title: str
    explanation: str
    severity: Literal["info", "review", "high"]
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
    model_name: str | None = None
    model_version: str | None = None


class ClaimAnalysis(BaseModel):
    schema_version: str = "1.0"
    claim_id: str
    trace_id: str
    created_at: str
    mode: Literal["fixture", "live"]
    human_review_required: bool = True
    analysis_status: Literal["complete", "partial", "blocked"] = "complete"
    priority: Literal["normal", "review", "high"]
    research_risk_score: float | None = Field(default=None, ge=0, le=1)
    risk_score_is_probability: bool = False
    evidence_completeness: float = Field(ge=0, le=1)
    missing_evidence: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    signals: list[Signal] = Field(default_factory=list)
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    graph_features: dict[str, Any] = Field(default_factory=dict)
    model_versions: dict[str, str] = Field(default_factory=dict)
    module_status: dict[str, dict[str, Any]] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ReviewRequest(BaseModel):
    reviewer_id: str = Field(min_length=2)
    decision: Literal["continue_processing", "request_evidence", "special_review"]
    reason: str = Field(min_length=10, max_length=2000)

    @field_validator("reason")
    @classmethod
    def reason_must_be_specific(cls, value: str) -> str:
        if len(value.split()) < 3:
            raise ValueError("Review reason must contain at least three words.")
        return value.strip()


class ReviewRecord(ReviewRequest):
    claim_id: str
    trace_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CorrectionRequest(BaseModel):
    reviewer_id: str = Field(min_length=2)
    document_id: str = Field(min_length=1)
    field_name: str = Field(min_length=1)
    original_value: Any = None
    corrected_value: Any
    reason: str = Field(min_length=10, max_length=2000)

    @field_validator("reason")
    @classmethod
    def correction_reason_must_be_specific(cls, value: str) -> str:
        if len(value.split()) < 3:
            raise ValueError("Correction reason must contain at least three words.")
        return value.strip()


class CorrectionRecord(CorrectionRequest):
    claim_id: str
    trace_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    mode: Literal["fixture", "live"]
    product_version: str
