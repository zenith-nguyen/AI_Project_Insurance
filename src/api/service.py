"""Fixture-first orchestration boundary; live adapters can implement the same contract."""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from collections.abc import Callable

from .schemas import AnalyzeRequest, CaptureSessionRecord, ClaimAnalysis, ClaimIntakeRecord, ClaimIntakeRequest, CorrectionRecord, CorrectionRequest, EvidenceUploadRecord, MediaAuthenticityReport, ReviewRecord, ReviewRequest
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

    def start_capture(self, claim_id: str) -> CaptureSessionRecord:
        return self.runtime_store.create_capture_session(claim_id)

    def upload(
        self, claim_id: str, kind: str, filename: str, content_type: str | None, content: bytes,
        capture_session_id: str | None = None, challenge_step: int | None = None,
    ) -> EvidenceUploadRecord:
        record = self.runtime_store.save_evidence(
            claim_id, kind, filename, content_type, content, capture_session_id, challenge_step,
        )
        self.analyses.pop(claim_id, None)
        if kind == "image":
            try:
                report = self.authenticity(claim_id, record.evidence_id)
                return record.model_copy(update={"authenticity_verdict": report.verdict})
            except Exception:
                return record.model_copy(update={"authenticity_verdict": "error"})
        return record

    def readiness(self) -> dict:
        return {
            "mode": "fixture",
            "fully_live": False,
            "modules": {"fixture": {"active": True, "reason": "Static prototype response"}},
        }

    def authenticity(self, claim_id: str, evidence_id: str) -> MediaAuthenticityReport:
        from src.media_authenticity import MediaAuthenticityAnalyzer

        matches = self.runtime_store.find_image_reuse(claim_id, evidence_id)
        cached = self.runtime_store.load_authenticity(claim_id, evidence_id)
        cached_matches = (cached or {}).get("image_info", {}).get("cross_claim_matches", [])
        if cached is not None and cached.get("analyzer_version") == MediaAuthenticityAnalyzer.version and cached_matches == matches:
            return MediaAuthenticityReport.model_validate(cached)
        path = self.runtime_store.evidence_path(claim_id, evidence_id)
        report = MediaAuthenticityAnalyzer().analyze(path, evidence_id=evidence_id, reuse_matches=matches)
        self.runtime_store.save_authenticity(claim_id, evidence_id, report.model_dump())
        return report

    def analyze(
        self, claim_id: str, request: AnalyzeRequest,
        progress: Callable[[str, str | None], None] | None = None,
    ) -> ClaimAnalysis:
        if progress:
            progress("preparing", None)
        if not request.force_recompute and not any([
            request.claim_amount is not None, request.incident_date, request.plate_number, request.evidence_ids,
        ]):
            cached = self.get_analysis(claim_id)
            if cached is not None:
                if progress:
                    progress("finalizing", "Đang dùng lại kết quả vì hồ sơ và bằng chứng không đổi.")
                return cached
        if progress:
            progress("evidence", None)
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
        payload.setdefault("required_evidence_count", 3)
        payload.setdefault("present_required_count", round(float(payload.get("evidence_completeness", 0)) * 3))
        analysis = ClaimAnalysis.model_validate(payload)
        self.analyses[claim_id] = analysis
        if progress:
            progress("finalizing", None)
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

    def events(self, claim_id: str) -> list[dict]:
        return [
            *({"event_type": "review", **record.model_dump()} for record in self.reviews.get(claim_id, [])),
            *({"event_type": "field_correction", **record.model_dump()} for record in self.corrections.get(claim_id, [])),
        ]

    def list_claims(self) -> list[dict]:
        rows = []
        for claim_id, analysis in self.analyses.items():
            events = self.events(claim_id)
            reviews = [item for item in events if item["event_type"] == "review"]
            latest = reviews[-1] if reviews else None
            rows.append({
                "claim_id": claim_id, "created_at": analysis.created_at, "incident_date": None,
                "plate_number": analysis.extracted_fields.get("plate_number"),
                "analysis_status": analysis.analysis_status, "priority": analysis.priority,
                "priority_reason": analysis.signals[0].title if analysis.signals else "Chưa có cờ tự động nổi bật",
                "research_risk_score": analysis.research_risk_score,
                "risk_score_available": analysis.research_risk_score is not None,
                "required_evidence_count": analysis.required_evidence_count,
                "present_required_count": analysis.present_required_count,
                "uploaded_file_count": sum(item.kind in {"image", "document"} for item in analysis.evidence),
                "missing_evidence": analysis.missing_evidence, "signal_count": len(analysis.signals),
                "high_signal_count": sum(item.severity == "high" for item in analysis.signals),
                "review_signal_count": sum(item.severity == "review" for item in analysis.signals),
                "latest_decision": latest.get("decision") if latest else None,
                "latest_reviewer": latest.get("reviewer_id") if latest else None,
                "latest_event_at": events[-1].get("created_at") if events else None,
                "event_count": len(events), "trace_id": analysis.trace_id,
            })
        return rows
