import json
from pathlib import Path

import pytest

from src.api.schemas import ClaimIntakeRequest
from src.api.storage import RuntimeClaimStore


def test_claim_intake_and_evidence_are_stored_with_hash(tmp_path: Path):
    store = RuntimeClaimStore(tmp_path)
    record = store.create(
        "CLM-UPLOAD-001",
        ClaimIntakeRequest(claim_amount=1200, incident_date="2026-10-13", plate_number="51A-12345"),
    )
    upload = store.save_evidence(
        record.claim_id,
        "document",
        "repair-estimate.pdf",
        "application/pdf",
        b"%PDF-1.4 research fixture",
    )

    assert upload.sha256 == "01db6f123d6fc2a576db2d8c4b5f06c867e2309014c6381c3ff9963492dbdf4c"
    manifest = json.loads((tmp_path / record.claim_id / "evidence_manifest.json").read_text(encoding="utf-8"))
    assert manifest[0]["original_filename"] == "repair-estimate.pdf"
    assert manifest[0]["stored_uri"].startswith("runtime://claims/CLM-UPLOAD-001/")


def test_claim_id_path_traversal_and_unsupported_files_are_rejected(tmp_path: Path):
    store = RuntimeClaimStore(tmp_path)
    with pytest.raises(ValueError):
        store.create("../escape", ClaimIntakeRequest())
    store.create("CLM-SAFE-001", ClaimIntakeRequest())
    with pytest.raises(ValueError):
        store.save_evidence("CLM-SAFE-001", "document", "malware.exe", "application/octet-stream", b"bad")
    with pytest.raises(ValueError):
        store.save_evidence("CLM-SAFE-001", "document", "fake.pdf", "application/pdf", b"not really a PDF")


def test_per_evidence_inference_cache_requires_matching_key(tmp_path: Path):
    store = RuntimeClaimStore(tmp_path)
    store.create("CLM-CACHE-001", ClaimIntakeRequest())
    upload = store.save_evidence(
        "CLM-CACHE-001", "document", "claim.pdf", "application/pdf", b"%PDF-1.4 cache fixture",
    )
    store.save_inference_cache(
        "CLM-CACHE-001", upload.evidence_id, "document", "file-and-model-v1",
        {"field": "cached"},
    )
    assert store.load_inference_cache(
        "CLM-CACHE-001", upload.evidence_id, "document", "file-and-model-v1",
    ) == {"field": "cached"}
    assert store.load_inference_cache(
        "CLM-CACHE-001", upload.evidence_id, "document", "different-model",
    ) is None
    with pytest.raises(ValueError):
        store.load_inference_cache("CLM-CACHE-001", upload.evidence_id, "../escape", "key")
