from pathlib import Path

import pytest

from src.document.classifier import Classification
from src.document.kie import HybridKIE, LayoutLMv3KIE, RuleBasedKIE
from src.document.metrics import character_error_rate, field_micro_scores, word_error_rate
from src.document.ocr import normalize_paddle_output
from src.document.pipeline import DocumentPipeline
from src.document.schema import BoundingBox, OCRToken


def test_normalizes_legacy_paddle_output():
    raw = [[[[0, 0], [10, 0], [10, 5], [0, 5]], ("Invoice", 0.9)]]
    tokens = normalize_paddle_output(raw)
    assert tokens[0].text == "Invoice"
    assert tokens[0].confidence == pytest.approx(0.9)
    assert tokens[0].bbox == BoundingBox(0, 0, 10, 5)


def test_normalizes_paddle_v3_output():
    raw = {"res": {"rec_texts": ["Total 1,250.00"], "rec_scores": [0.95], "rec_polys": [[[0, 0], [4, 0], [4, 1], [0, 1]]]}}
    tokens = normalize_paddle_output(raw)
    assert tokens[0].text == "Total 1,250.00"
    assert tokens[0].confidence == pytest.approx(0.95)


def test_rule_kie_extracts_normalized_fields():
    tokens = [OCRToken("Invoice No: AB-1234 Date 11/10/2026 Total: 1,250.00 VND Plate 51A-12345", 0.9)]
    fields = {field.field_name: field for field in RuleBasedKIE().extract(tokens)}
    assert fields["document_number"].normalized_value == "AB-1234"
    assert fields["document_date"].normalized_value == "2026-10-11"
    assert fields["total_amount"].normalized_value == 1250.0
    assert fields["plate_number"].normalized_value == "51A12345"


def test_rule_kie_recovers_iso_date_and_largest_vnd_amount():
    tokens = [
        OCRToken("Ngày 2026-10-09 Biển số 59H-246.81", 0.95),
        OCRToken("Hạng mục 3,792,000 VND", 0.94),
        OCRToken("TÒNG D TOÁN 31,600,000 VND", 0.93),
    ]
    fields = {field.field_name: field for field in RuleBasedKIE().extract(tokens)}
    assert fields["document_date"].normalized_value == "2026-10-09"
    assert fields["total_amount"].normalized_value == 31_600_000.0
    assert fields["plate_number"].normalized_value == "59H24681"


def test_hybrid_kie_keeps_valid_model_field_and_fills_missing_rules():
    class Primary:
        model_name = "layoutlmv3"
        model_version = "candidate"

        def extract(self, tokens, image=None):
            from src.document.schema import ExtractedField
            return [ExtractedField("document_date", "09/10/2026", "2026-10-09", 0.8, method="layoutlmv3")]

    tokens = [OCRToken("Date 09/10/2026 Total 31,600,000 VND Plate 59H-246.81", 0.9)]
    fields = {field.field_name: field for field in HybridKIE(Primary()).extract(tokens)}
    assert fields["document_date"].method == "layoutlmv3"
    assert fields["total_amount"].normalized_value == 31_600_000.0
    assert fields["total_amount"].method == "rule_fallback"
    assert fields["plate_number"].method == "rule_fallback"


def test_hybrid_kie_exposes_conflict_and_overrides_low_confidence_model_value():
    class Primary:
        model_name = "layoutlmv3"
        model_version = "candidate"

        def extract(self, tokens, image=None):
            from src.document.schema import ExtractedField
            return [ExtractedField(
                "total_amount", "14,442,000", 14_442_000.0, 0.68,
                method="layoutlmv3",
            )]

    hybrid = HybridKIE(Primary(), conflict_confidence_threshold=0.75)
    tokens = [OCRToken("TONG CONG 24,900,000 VND", 0.94)]
    fields = {field.field_name: field for field in hybrid.extract(tokens)}
    assert fields["total_amount"].normalized_value == 24_900_000.0
    assert fields["total_amount"].method == "rule_override_low_confidence"
    assert hybrid.last_warnings == ["kie_model_rule_conflict:total_amount"]


def test_hybrid_kie_keeps_high_confidence_model_value_but_exposes_conflict():
    class Primary:
        model_name = "layoutlmv3"
        model_version = "candidate"

        def extract(self, tokens, image=None):
            from src.document.schema import ExtractedField
            return [ExtractedField(
                "total_amount", "24,900,000", 24_900_000.0, 0.91,
                method="layoutlmv3",
            )]

    hybrid = HybridKIE(Primary(), conflict_confidence_threshold=0.75)
    fields = {field.field_name: field for field in hybrid.extract([
        OCRToken("TONG CONG 14,442,000 VND", 0.94)
    ])}
    assert fields["total_amount"].normalized_value == 24_900_000.0
    assert fields["total_amount"].method == "layoutlmv3"
    assert hybrid.last_warnings == ["kie_model_rule_conflict:total_amount"]


def test_base_layoutlm_checkpoint_is_rejected_before_import():
    with pytest.raises(ValueError, match="fine-tuned"):
        LayoutLMv3KIE("microsoft/layoutlmv3-base")


def test_layoutlm_bio_span_recovery():
    assert LayoutLMv3KIE._spans(["O", "B-DATE", "I-DATE", "O", "B-TOTAL"]) == [
        ("DATE", 1, 3), ("TOTAL", 4, 5)
    ]


def test_document_metrics():
    assert character_error_rate(["abc"], ["adc"]) == pytest.approx(1 / 3)
    assert word_error_rate(["one two"], ["one too"]) == pytest.approx(0.5)
    assert field_micro_scores([("date", "2026")], [("date", "2026")])["f1"] == 1.0


def test_pipeline_returns_stable_contract():
    class Classifier:
        model_name = "mock-classifier"
        model_version = "v1"

        def predict(self, images):
            return [Classification("invoice", 0.9, {"invoice": 0.9})]

    class OCR:
        model_name = "mock-ocr"
        model_version = "v1"

        def predict(self, image):
            return [OCRToken("Total: 100 VND", 0.8)]

    stages = []
    result = DocumentPipeline(Classifier(), OCR(), RuleBasedKIE()).process(
        Path("invoice.png"), "CLM-1", "DOC-1", progress=stages.append
    )
    assert result.document_type == "invoice"
    assert result.fields[0].field_name == "total_amount"
    assert result.model_versions["classifier"] == "mock-classifier@v1"
    assert result.trace_id
    assert stages == ["document_classifier", "document_ocr", "document_kie"]
