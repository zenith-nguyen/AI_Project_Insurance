"""Conservative routing of research analyses to a human review queue."""
from __future__ import annotations

from .schemas import ClaimAnalysis, VerifyResponse


def route_analysis(analysis: ClaimAnalysis) -> VerifyResponse:
    reasons: list[str] = []
    if analysis.analysis_status != "complete" or analysis.research_risk_score is None:
        reasons.append("Phân tích chưa hoàn tất hoặc chưa có điểm xếp hạng hợp lệ.")
    if analysis.missing_evidence or analysis.evidence_completeness < 1:
        reasons.append("Thiếu bằng chứng bắt buộc; cần yêu cầu bổ sung.")

    tabular = next((s for s in analysis.signals if s.signal_id == "tabular-priority"), None)
    if reasons:
        action = "SUPPLEMENT"
    elif tabular and tabular.severity == "high":
        action = "SIU"
        reasons.append("Điểm bảng vượt ngưỡng t2 của model artifact; cần SIU xem xét.")
    elif analysis.priority == "high" or any(s.severity == "high" for s in analysis.signals):
        action = "SIU"
        reasons.append("Có tín hiệu mức cao; chuyển người phụ trách xem xét chuyên sâu.")
    elif tabular and tabular.severity == "review":
        action = "SUPPLEMENT"
        reasons.append("Điểm bảng nằm trong hàng đợi t1–t2; cần reviewer đối chiếu.")
    elif analysis.priority == "review" or any(s.severity == "review" for s in analysis.signals):
        action = "SUPPLEMENT"
        reasons.append("Có tín hiệu cần đối chiếu thủ công trước khi xử lý tiếp.")
    else:
        action = "STP"
        reasons.append("Chưa thấy tín hiệu cần chuyển tuyến trong phân tích hiện tại.")

    if analysis.mode == "fixture":
        reasons.append("Kết quả fixture chỉ dùng để trình diễn; không áp dụng cho hồ sơ thật.")
    evidence_refs = sorted({ref for signal in analysis.signals for ref in signal.evidence_ids})
    return VerifyResponse(
        claim_id=analysis.claim_id, trace_id=analysis.trace_id,
        action=action, reasons=reasons, research_risk_score=analysis.research_risk_score,
        risk_score=analysis.research_risk_score,
        risk_score_is_probability=False, analysis_status=analysis.analysis_status,
        human_review_required=True, mode=analysis.mode,
        model_version=analysis.model_versions.get("tabular_risk"),
        evidence_refs=evidence_refs,
    )
