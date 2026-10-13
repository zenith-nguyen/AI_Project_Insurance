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
