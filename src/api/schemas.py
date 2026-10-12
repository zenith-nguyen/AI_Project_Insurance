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


class Evidence(BaseModel):
    evidence_id: str
    kind: Literal["claim", "image", "document", "relationship"]
    label: str
    source_uri: str | None = None
    observed_at: str | None = None


class Signal(BaseModel):
    signal_id: str
    category: Literal["risk", "damage", "document", "consistency", "relationship"]
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


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    mode: Literal["fixture", "live"]
    product_version: str
