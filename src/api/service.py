"""Fixture-first orchestration boundary; live adapters can implement the same contract."""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .schemas import AnalyzeRequest, ClaimAnalysis, ClaimIntakeRecord, ClaimIntakeRequest, CorrectionRecord, CorrectionRequest, EvidenceUploadRecord, MediaAuthenticityReport, ReviewRecord, ReviewRequest
from .storage import RuntimeClaimStore


class FixtureClaimService:
    def __init__(self, fixture_path: str | Path, runtime_claim_root: str | Path | None = None) -> None:
        self.fixture_path = Path(fixture_path)
        self.template = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        self.analyses: dict[str, ClaimAnalysis] = {}
        self.reviews: dict[str, list[ReviewRecord]] = {}
        self.corrections: dict[str, list[CorrectionRecord]] = {}
        self.runtime_store = RuntimeClaimStore(runtime_claim_root or self.fixture_path.parent / "runtime_claims")

    def intake(self, claim_id: str, request: ClaimIntakeRequest) -> ClaimIntakeRecord:
        return self.runtime_store.create(claim_id, request)

    def upload(self, claim_id: str, kind: str, filename: str, content_type: str | None, content: bytes) -> EvidenceUploadRecord:
        return self.runtime_store.save_evidence(claim_id, kind, filename, content_type, content)

    def authenticity(self, claim_id: str, evidence_id: str) -> MediaAuthenticityReport:
        from src.media_authenticity import MediaAuthenticityAnalyzer

        path = self.runtime_store.evidence_path(claim_id, evidence_id)
        return MediaAuthenticityAnalyzer().analyze(path, evidence_id=evidence_id)

    def analyze(self, claim_id: str, request: AnalyzeRequest) -> ClaimAnalysis:
        payload = copy.deepcopy(self.template)
        payload.update(
            claim_id=claim_id,
            trace_id=uuid4().hex,
            created_at=datetime.now(timezone.utc).isoformat(),
            mode="fixture",
        )
        if request.claim_amount is not None:
            payload["extracted_fields"]["claim_amount"] = request.claim_amount
        if request.incident_date:
            payload["extracted_fields"]["incident_date"] = request.incident_date
        if request.plate_number:
            payload["extracted_fields"]["plate_number"] = request.plate_number
        analysis = ClaimAnalysis.model_validate(payload)
        self.analyses[claim_id] = analysis
        return analysis

    def get_analysis(self, claim_id: str) -> ClaimAnalysis | None:
        return self.analyses.get(claim_id)

    def review(self, claim_id: str, request: ReviewRequest) -> ReviewRecord:
        analysis = self.get_analysis(claim_id)
        if analysis is None:
            raise KeyError(claim_id)
        record = ReviewRecord(claim_id=claim_id, trace_id=analysis.trace_id, **request.model_dump())
        self.reviews.setdefault(claim_id, []).append(record)
        return record

    def correct(self, claim_id: str, request: CorrectionRequest) -> CorrectionRecord:
        analysis = self.get_analysis(claim_id)
        if analysis is None:
            raise KeyError(claim_id)
        record = CorrectionRecord(claim_id=claim_id, trace_id=analysis.trace_id, **request.model_dump())
        self.corrections.setdefault(claim_id, []).append(record)
        return record
