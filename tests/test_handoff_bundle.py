import json
import zipfile

import pytest

from scripts.build_handoff_bundle import build, build_compact


def test_numbered_draft_handoff_bundle_contains_pdf_contract_and_checksums(tmp_path):
    package, archive = build(tmp_path, "draft", "test-v1")
    assert archive.is_file()
    assert (package / "00-08_HANDBOOK/00_START_HERE.md").is_file()
    assert (package / "00-08_HANDBOOK/00_START_HERE.pdf").read_bytes().startswith(b"%PDF")
    assert (package / "90_CONTRACTS/claim_review_openapi.v1.json").is_file()
    checksums = (package / "SHA256SUMS.txt").read_text()
    assert "00-08_HANDBOOK/07_RELEASE_SECURITY_AND_UAT.pdf" in checksums
    assert "00-08_HANDBOOK/08_DEFINITION_OF_DONE.pdf" in checksums
    manifest = json.loads((package / "RELEASE_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "draft"
    with zipfile.ZipFile(archive) as bundle:
        assert any(name.endswith("SHA256SUMS.txt") for name in bundle.namelist())


def test_final_bundle_requires_explicit_gate_confirmation(tmp_path):
    with pytest.raises(ValueError, match="confirm-gates"):
        build(tmp_path, "final", "test-v1")


def test_confirmation_cannot_bypass_definition_of_done(tmp_path):
    with pytest.raises(ValueError, match="Definition of Done"):
        build(tmp_path, "final", "test-v1", confirm_gates=True)


def test_compact_bundle_has_few_recipient_facing_files(tmp_path):
    package, archive = build_compact(tmp_path, "draft", "test-v1")
    assert archive.is_file()
    assert (package / "00_HUONG_DAN_BAT_DAU.md").is_file()
    assert (package / "00_HUONG_DAN_BAT_DAU.pdf").read_bytes().startswith(b"%PDF")
    assert (package / "01_GITHUB_CAI_DAT_VA_CAP_NHAT.md").is_file()
    assert (package / "04_UI_HTML_MAU.html").is_file()
    assert (package / "05_OPENAPI.json").is_file()
    manifest = json.loads((package / "07_RELEASE_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "draft"
    assert manifest["research_handoff_done"] is False
    assert len([path for path in package.iterdir() if path.is_file()]) <= 10
