import json
from pathlib import Path

from scripts.build_business_demo_pack import CASES, SOURCE_FILES, build


def test_business_demo_pack_has_ordered_cases_and_integrity_manifest(tmp_path: Path):
    source = tmp_path / "source"
    for index, relative in enumerate(SOURCE_FILES.values(), start=1):
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"synthetic-fixture-{index}".encode())

    output = build(source, tmp_path / "00_TEST_CLAIM_REVIEW_BUSINESS")

    expected = json.loads((output / "02_KET_QUA_MONG_DOI.json").read_text(encoding="utf-8"))
    manifest = json.loads((output / "99_MANIFEST_SHA256.json").read_text(encoding="utf-8"))
    assert expected["run_in_order"] == [case["folder"] for case in CASES]
    assert manifest["case_count"] == 9
    assert all(len(item["sha256"]) == 64 for item in manifest["files"])
    assert (output / "04_ANH_AI_KHONG_MARKER/00_THUC_HIEN_VA_KET_QUA.md").is_file()
    assert "không đủ để chứng minh ảnh thật" in (
        output / "04_ANH_AI_KHONG_MARKER/00_THUC_HIEN_VA_KET_QUA.md"
    ).read_text(encoding="utf-8-sig")
    assert "Dùng hồ sơ mẫu: TẮT" in (
        output / "09_KHONG_CO_FEATURE_BANG/00_THUC_HIEN_VA_KET_QUA.md"
    ).read_text(encoding="utf-8-sig")
