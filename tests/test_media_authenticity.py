from pathlib import Path

from PIL import Image

from src.media_authenticity import MediaAuthenticityAnalyzer


def save_jpeg(path: Path, *, software: str | None = None) -> None:
    image = Image.new("RGB", (16, 12), (30, 80, 120))
    exif = Image.Exif()
    if software:
        exif[305] = software
    image.save(path, format="JPEG", exif=exif)


def test_missing_metadata_remains_inconclusive(tmp_path):
    path = tmp_path / "camera.jpg"
    save_jpeg(path)
    report = MediaAuthenticityAnalyzer(exiftool="", c2patool="").analyze(path, evidence_id="EV-1")

    assert report.verdict == "inconclusive"
    assert report.human_review_required is False
    assert any(item.code == "metadata_absent" for item in report.findings)
    assert any("not evidence" in limitation for limitation in report.limitations)
    coverage = report.image_info["assessment_coverage"]
    assert coverage["is_truth_score"] is False
    assert "metadata" in coverage["performed_layers"]
    assert "calibrated_pixel_model" in coverage["unavailable_layers"]


def test_ai_generator_metadata_is_a_review_signal(tmp_path):
    path = tmp_path / "generated.jpg"
    save_jpeg(path, software="Stable Diffusion / ComfyUI")
    report = MediaAuthenticityAnalyzer(exiftool="", c2patool="").analyze(path)

    assert report.verdict == "review"
    assert report.human_review_required is True
    assert any(item.source == "metadata" and item.outcome == "detected" for item in report.findings)


def test_signed_ai_assertion_has_strongest_verdict(tmp_path):
    path = tmp_path / "credential.jpg"
    save_jpeg(path)
    report = MediaAuthenticityAnalyzer(
        exiftool="",
        c2pa_runner=lambda _: {
            "active_manifest": "urn:test",
            "assertions": [{"digitalSourceType": "trainedAlgorithmicMedia"}],
            "claim_generator": "test generator",
        },
    ).analyze(path)

    assert report.verdict == "ai_provenance_detected"
    assert any(item.code == "c2pa_ai_assertion_present" for item in report.findings)


def test_calibrated_pixel_forensics_is_a_screening_signal(tmp_path):
    path = tmp_path / "pixel-candidate.jpg"
    save_jpeg(path)
    report = MediaAuthenticityAnalyzer(
        exiftool="", c2patool="",
        forensic_runner=lambda _: {
            "model_name": "fixture-forensics", "model_version": "v1", "benchmark_id": "locked-v1",
            "domain": "insurance-fixture", "score_ai": 0.96, "threshold_review": 0.8,
            "threshold_high": 0.95, "calibrated": True,
        },
    ).analyze(path)

    finding = next(item for item in report.findings if item.code == "forensic_model_high_score")
    assert finding.severity == "high"
    assert report.verdict == "review"
    assert report.image_info["forensic_model"]["benchmark_id"] == "locked-v1"


def test_uncalibrated_pixel_forensics_fails_closed(tmp_path):
    path = tmp_path / "uncalibrated.jpg"
    save_jpeg(path)
    report = MediaAuthenticityAnalyzer(
        exiftool="", c2patool="",
        forensic_runner=lambda _: {
            "score_ai": 0.99, "threshold_review": 0.8, "threshold_high": 0.95, "calibrated": False,
        },
    ).analyze(path)

    assert report.verdict == "inconclusive"
    assert any(item.code == "forensic_model_error" for item in report.findings)
