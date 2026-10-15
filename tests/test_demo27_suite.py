from pathlib import Path

import pytest

import hashlib
import json

from src.evaluation.demo_suite import find_pack_root, unique_paths, validate_prepared_demo_suite
from scripts.import_demo27_case import _point_in_time_history


def test_find_pack_root_accepts_outer_or_inner_folder(tmp_path: Path):
    inner = tmp_path / "decomposed-export-name"
    inner.mkdir()
    (inner / "BAT_DAU_O_DAY.md").write_text("start", encoding="utf-8")
    assert find_pack_root(tmp_path) == inner.resolve()
    assert find_pack_root(inner) == inner.resolve()


def test_find_pack_root_rejects_ambiguous_export(tmp_path: Path):
    for name in ("a", "b"):
        folder = tmp_path / name
        folder.mkdir()
        (folder / "BAT_DAU_O_DAY.md").write_text("start", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="found 2"):
        find_pack_root(tmp_path)


def test_unique_paths_normalizes_separators_and_preserves_order():
    assert unique_paths(["a\\b.png", "a/b.png", "c.pdf", "a/b.png"]) == ["a/b.png", "c.pdf"]


def test_validate_prepared_suite_checks_integrity_and_case_paths(tmp_path: Path):
    (tmp_path / "cases/C1").mkdir(parents=True)
    (tmp_path / "expected_private").mkdir()
    (tmp_path / "assets").mkdir()
    files = {
        "cases/C1/claim.json": "{}\n",
        "expected_private/C1.json": "{}\n",
        "assets/image.png": "fixture",
    }
    rows = []
    for relative, content in files.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        rows.append({
            "path": relative, "size": target.stat().st_size,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        })
    suite = {
        "case_count": 1, "data_classification": {"domain_accuracy_claim_allowed": False},
        "cases": [{
            "claim_id": "C1", "claim_file": "cases/C1/claim.json", "expected_file": "expected_private/C1.json",
            "vehicle_images": ["assets/image.png"], "minimal_documents": [], "full_documents": [],
        }],
    }
    (tmp_path / "suite_manifest.json").write_text(json.dumps(suite), encoding="utf-8")
    (tmp_path / "integrity_manifest.json").write_text(json.dumps({"files": rows}), encoding="utf-8")
    assert validate_prepared_demo_suite(tmp_path)["passed"] is True

    (tmp_path / "assets/image.png").write_text("changed", encoding="utf-8")
    result = validate_prepared_demo_suite(tmp_path)
    assert result["passed"] is False
    assert result["hash_or_size_mismatches"] == ["assets/image.png"]


def test_point_in_time_history_rebases_future_synthetic_references():
    rows = [
        {"claim_id": "TARGET", "submitted_at": "2026-09-22T09:00:00+07:00"},
        {"claim_id": "REF-1", "submitted_at": "2026-09-23T09:00:00+07:00"},
        {"claim_id": "REF-2", "submitted_at": "2026-09-24T09:00:00+07:00"},
    ]
    prepared = _point_in_time_history(rows, "TARGET", "2026-09-22T09:00:00+07:00")
    assert [row["submitted_at"] for row in prepared] == [
        "2026-09-21T09:00:00+07:00", "2026-09-20T09:00:00+07:00",
    ]
    assert all(row["timestamp_rebased_for_point_in_time_uat"] for row in prepared)
