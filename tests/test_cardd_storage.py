import json
import os

import pytest

from scripts.materialize_cardd_training_view import materialize
from scripts.slim_cardd_yolo_storage import slim


def build_fixture(tmp_path):
    bronze = tmp_path / "bronze"
    converted = tmp_path / "converted"
    (bronze / "data").mkdir(parents=True)
    (converted / "images/train").mkdir(parents=True)
    (converted / "labels/train").mkdir(parents=True)
    (bronze / "data/example.jpg").write_bytes(b"image")
    (converted / "images/train/example.jpg").write_bytes(b"image")
    (converted / "labels/train/example.txt").write_text("0 0 0 1 0 1 1\n", encoding="utf-8")
    (converted / "conversion_report.json").write_text(
        json.dumps({"images": 1, "classes": ["damage"]}), encoding="utf-8"
    )
    (converted / "split_manifest.jsonl").write_text(
        json.dumps({"image": "example.jpg", "split": "train", "instances": 1}) + "\n",
        encoding="utf-8",
    )
    (converted / "data.yaml").write_text("path: old\n", encoding="utf-8")

    return bronze, converted


def test_slim_cardd_removes_only_redundant_images(tmp_path):
    bronze, converted = build_fixture(tmp_path)
    slim_report = slim(bronze, converted)

    assert not (converted / "images").exists()
    assert (bronze / "data/example.jpg").is_file()
    assert (converted / "labels/train/example.txt").is_file()
    assert (converted / "storage_manifest.json").is_file()
    assert slim_report["removed_duplicate_image_files"] == 1
    assert slim(bronze, converted)["already_slim"] is True


@pytest.mark.skipif(os.name == "nt", reason="Windows symlinks require developer-mode privileges")
def test_materialize_cardd_uses_links_without_persistent_copy(tmp_path):
    bronze, converted = build_fixture(tmp_path)
    slim(bronze, converted)
    target = tmp_path / "training_view"
    view_report = materialize(bronze, converted, target)

    assert (target / "images/train/example.jpg").is_symlink()
    assert (target / "labels/train/example.txt").is_symlink()
    assert view_report["persistent_image_bytes_added"] == 0


def test_materialize_cardd_can_copy_into_ephemeral_training_view(tmp_path):
    bronze, converted = build_fixture(tmp_path)
    slim(bronze, converted)
    target = tmp_path / "copied_training_view"

    view_report = materialize(bronze, converted, target, image_mode="copy")

    assert (target / "images/train/example.jpg").read_bytes() == b"image"
    assert not (target / "images/train/example.jpg").is_symlink()
    assert (target / "labels/train/example.txt").is_file()
    assert view_report["image_mode"] == "copy"
    assert view_report["image_bytes_materialized"] == 5
