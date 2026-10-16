from datetime import date
from pathlib import Path

from src.document.policy import DocumentPolicyRegistry
from src.document.quality import assess_document_readability
from src.document.schema import OCRToken


ROOT = Path(__file__).resolve().parents[1]


def test_readability_routes_clear_print_without_claiming_handwriting_detection():
    result = assess_document_readability([
        OCRToken("CÔNG TY BẢO HIỂM", 0.96),
        OCRToken("Tổng tiền 12.500.000 VND", 0.93),
    ])
    assert result["state"] == "printed_likely"
    assert result["human_review_required"] is False
    assert result["handwriting_model_active"] is False


def test_readability_flags_low_confidence_fragments_for_human_route():
    result = assess_document_readability([
        OCRToken("N", 0.41), OCRToken("12", 0.52), OCRToken("?", 0.33), OCRToken("ký", 0.48),
    ])
    assert result["state"] == "handwriting_or_low_quality_review"
    assert result["human_review_required"] is True
    assert result["low_confidence_ratio"] == 1.0
    assert "không phải kết luận" in result["limitations"][0].lower()


def test_vietnam_document_policy_exposes_current_and_due_states():
    registry = DocumentPolicyRegistry.load(ROOT / "configs/vietnam_document_policy.v1.yaml")
    current = registry.public_summary(as_of=date(2026, 10, 16))
    overdue = registry.public_summary(as_of=date(2026, 12, 1))
    assert current["jurisdiction"] == "VN"
    assert current["automatic_legal_updates"] is False
    assert current["counts"]["current_reviewed"] == 4
    assert overdue["counts"]["review_due"] == 4
    assert current["official_sources"]["national_legal_database"]["url"].startswith("https://vbpl.vn/")
