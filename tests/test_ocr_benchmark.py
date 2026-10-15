import hashlib
import json

import pytest

from src.document.ocr_benchmark import compare_ocr_reports, evaluate_ocr, load_ground_truth, load_predictions, normalize_text


def _write_jsonl(path, rows):
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def _dataset(tmp_path):
    image = tmp_path / "page.bin"
    image.write_bytes(b"private-image-fixture")
    transcript = tmp_path / "page.txt"
    transcript.write_text("Tổng tiền: 1.000.000 đ\nNgày 16/10/2026", encoding="utf-8")
    manifest = tmp_path / "manifest.jsonl"
    _write_jsonl(manifest, [{
        "sample_id": "VN-OCR-001",
        "split": "validation",
        "image_path": image.name,
        "image_sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
        "document_type": "repair_estimate",
        "reference_text_path": transcript.name,
        "annotation_status": "adjudicated",
        "consent_or_legal_basis": "synthetic-test",
        "pii_treatment": "synthetic",
    }])
    return manifest


def test_normalization_preserves_vietnamese_diacritics_and_line_order():
    assert normalize_text("  To\u0302̉ng   tie\u0302̀n \r\n  Nga\u0300y  ") == "Tổng tiền\nNgày"


def test_manifest_and_prediction_evaluation_excludes_raw_text(tmp_path):
    manifest = _dataset(tmp_path)
    predictions_path = tmp_path / "predictions.jsonl"
    _write_jsonl(predictions_path, [{
        "sample_id": "VN-OCR-001",
        "predicted_text": "Tong tien: 1.000.000 đ\nNgày 16/10/2026",
        "latency_seconds": 2.5,
    }])
    truth = load_ground_truth(manifest)
    result = evaluate_ocr(truth, load_predictions(predictions_path), minimum_pages=50)
    assert result["overall"]["pages"] == 1
    assert result["overall"]["cer"] > 0
    assert result["latency_seconds"]["p95"] == 2.5
    assert result["gate"]["passed"] is False
    assert "reference_text" not in json.dumps(result, ensure_ascii=False)


def test_manifest_rejects_hash_mismatch(tmp_path):
    manifest = _dataset(tmp_path)
    row = json.loads(manifest.read_text(encoding="utf-8"))
    row["image_sha256"] = "0" * 64
    _write_jsonl(manifest, [row])
    with pytest.raises(ValueError, match="SHA-256"):
        load_ground_truth(manifest)


def test_manifest_requires_adjudication(tmp_path):
    manifest = _dataset(tmp_path)
    row = json.loads(manifest.read_text(encoding="utf-8"))
    row["annotation_status"] = "draft"
    _write_jsonl(manifest, [row])
    with pytest.raises(ValueError, match="adjudicated"):
        load_ground_truth(manifest)


def test_evaluation_rejects_incomplete_prediction_coverage(tmp_path):
    truth = load_ground_truth(_dataset(tmp_path))
    with pytest.raises(ValueError, match="coverage mismatch"):
        evaluate_ocr(truth, {}, minimum_pages=1)


def test_synthetic_engineering_tier_never_unlocks_domain_claim(tmp_path):
    manifest = _dataset(tmp_path)
    row = json.loads(manifest.read_text(encoding="utf-8"))
    row["benchmark_tier"] = "synthetic_engineering"
    row["annotation_status"] = "source_verified"
    _write_jsonl(manifest, [row])
    predictions_path = tmp_path / "predictions.jsonl"
    _write_jsonl(predictions_path, [{
        "sample_id": "VN-OCR-001", "predicted_text": "x", "latency_seconds": 1,
    }])
    result = evaluate_ocr(load_ground_truth(manifest), load_predictions(predictions_path), minimum_pages=1)
    assert result["gate"]["passed"] is True
    assert result["benchmark_tier"] == "synthetic_engineering"
    assert result["gate"]["enough_pages_for_domain_claim"] is False


def test_business_field_accuracy_matches_formatted_values(tmp_path):
    manifest = _dataset(tmp_path)
    row = json.loads(manifest.read_text(encoding="utf-8"))
    row["reference_fields"] = {
        "total_vnd": "3600000", "document_date": "22/09/2026", "plate_number": "51A-123.45",
    }
    _write_jsonl(manifest, [row])
    predictions_path = tmp_path / "predictions.jsonl"
    _write_jsonl(predictions_path, [{
        "sample_id": "VN-OCR-001",
        "predicted_text": "Ngày 22-09-2026\nBiển số 51A 12345\nTỔNG CỘNG 3.600.000 VND",
        "latency_seconds": 1,
    }])
    result = evaluate_ocr(load_ground_truth(manifest), load_predictions(predictions_path), minimum_pages=1)
    assert {name: item["exact_presence_rate"] for name, item in result["business_field_accuracy"].items()} == {
        "document_date": 1.0, "plate_number": 1.0, "total_vnd": 1.0,
    }


def test_candidate_promotion_requires_quality_fields_and_latency():
    baseline = {
        "benchmark_tier": "synthetic_engineering", "gate": {"passed": True},
        "overall": {"pages": 27, "cer": 0.4}, "latency_seconds": {"mean": 20.0},
        "business_field_accuracy": {"total_vnd": {"exact_presence_rate": 0.8}},
    }
    candidate = {
        "benchmark_tier": "synthetic_engineering", "gate": {"passed": True},
        "overall": {"pages": 27, "cer": 0.3}, "latency_seconds": {"mean": 10.0},
        "business_field_accuracy": {"total_vnd": {"exact_presence_rate": 0.9}},
    }
    assert compare_ocr_reports(baseline, candidate)["selected"] is True
    candidate["business_field_accuracy"]["total_vnd"]["exact_presence_rate"] = 0.7
    result = compare_ocr_reports(baseline, candidate)
    assert result["selected"] is False
    assert result["checks"]["business_field_non_regression"] is False
