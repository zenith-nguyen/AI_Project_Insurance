import json
from pathlib import Path

import pytest

pytest.importorskip("networkx")

from src.api.live import LiveClaimService
from src.api.schemas import AnalyzeRequest, CorrectionRequest, ReviewRequest
from src.registry import load_registry


ROOT = Path(__file__).resolve().parents[1]


def service(tmp_path: Path) -> LiveClaimService:
    return LiveClaimService(
        ROOT,
        load_registry(ROOT / "configs/model_registry.v1.yaml"),
        tmp_path / "reviews.jsonl",
    )


def test_golden_claim_runs_real_tabular_rules_and_graph(tmp_path):
    live = service(tmp_path)
    result = live.analyze("CLM-GOLD-001", AnalyzeRequest())

    assert result.mode == "live"
    assert result.claim_id == "CLM-GOLD-001"
    assert result.research_risk_score is not None
    assert result.risk_score_is_probability is False
    assert result.graph_features["shared_entity_count"] == 1
    assert {signal.category for signal in result.signals}.issuperset({"consistency", "relationship"})
    assert result.model_versions == {
        "tabular_risk": "tabular_v1",
        "consistency": "consistency_v1",
        "relationships": "point_in_time_v1",
    }
    assert any("YOLO was not invoked" in warning for warning in result.warnings)


def test_review_is_persisted_as_jsonl(tmp_path):
    live = service(tmp_path)
    live.analyze("CLM-GOLD-002", AnalyzeRequest())
    record = live.review(
        "CLM-GOLD-002",
        ReviewRequest(
            reviewer_id="reviewer-01",
            decision="request_evidence",
            reason="Cần bổ sung ảnh toàn cảnh",
        ),
    )

    stored = json.loads((tmp_path / "reviews.jsonl").read_text(encoding="utf-8"))
    assert stored["event_type"] == "review"
    assert stored["claim_id"] == record.claim_id
    assert stored["trace_id"] == record.trace_id


def test_field_correction_is_persisted_with_provenance(tmp_path):
    live = service(tmp_path)
    live.analyze("CLM-GOLD-001", AnalyzeRequest())
    record = live.correct(
        "CLM-GOLD-001",
        CorrectionRequest(
            reviewer_id="reviewer-01",
            document_id="DOC-001",
            field_name="total_amount",
            original_value=61680,
            corrected_value=61600,
            reason="Đối chiếu lại ảnh chứng từ gốc",
        ),
    )

    stored = json.loads((tmp_path / "reviews.jsonl").read_text(encoding="utf-8"))
    assert stored["event_type"] == "field_correction"
    assert stored["claim_id"] == record.claim_id
    assert stored["field_name"] == "total_amount"


def test_unknown_golden_claim_is_rejected(tmp_path):
    with pytest.raises(KeyError):
        service(tmp_path).analyze("CLM-GOLD-999", AnalyzeRequest())


def test_all_golden_claim_expectations_are_satisfied(tmp_path):
    live = service(tmp_path)
    for expected_file in sorted((ROOT / "data/golden/claims").glob("*/expected_analysis.json")):
        expected = json.loads(expected_file.read_text(encoding="utf-8"))
        result = live.analyze(expected["claim_id"], AnalyzeRequest())
        categories = {signal.category for signal in result.signals}
        assert result.human_review_required is expected["human_review_required"]
        assert categories.issuperset(expected["required_signal_categories"])
