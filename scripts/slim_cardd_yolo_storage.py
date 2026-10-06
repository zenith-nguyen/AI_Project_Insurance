"""Remove duplicated YOLO image copies after verifying Bronze and labels are complete."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def slim(bronze: Path, converted: Path) -> dict:
    bronze = bronze.resolve()
    converted = converted.resolve()
    report_path = converted / "conversion_report.json"
    manifest_path = converted / "split_manifest.jsonl"
    images_dir = converted / "images"
    labels_dir = converted / "labels"
    if not all(path.exists() for path in (report_path, manifest_path, images_dir, labels_dir)):
        raise FileNotFoundError("Converted dataset is missing report, manifest, images, or labels")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line]
    expected = int(report["images"])
    if len(rows) != expected:
        raise ValueError(f"Manifest has {len(rows)} rows; expected {expected}")

    missing_bronze = []
    missing_labels = []
    for row in rows:
        image_name, split = row["image"], row["split"]
        if not (bronze / "data" / image_name).is_file():
            missing_bronze.append(image_name)
        if not (labels_dir / split / f"{Path(image_name).stem}.txt").is_file():
            missing_labels.append(image_name)
    if missing_bronze or missing_labels:
        raise ValueError(
            f"Refusing cleanup: {len(missing_bronze)} Bronze images and "
            f"{len(missing_labels)} YOLO labels are missing"
        )

    image_files = [
        path for path in images_dir.rglob("*")
        if path.is_file() and path.suffix.casefold() in IMAGE_SUFFIXES
    ]
    if len(image_files) != expected:
        raise ValueError(f"Converted images has {len(image_files)} files; expected {expected}")
    bytes_removed = sum(path.stat().st_size for path in image_files)
    shutil.rmtree(images_dir)
    data_yaml = converted / "data.yaml"
    if data_yaml.exists():
        data_yaml.replace(converted / "data.requires_materialization.yaml")
    storage_report = {
        "storage_mode": "labels-and-manifest-only",
        "bronze_root": str(bronze),
        "converted_root": str(converted),
        "verified_bronze_images": expected,
        "verified_yolo_labels": expected,
        "removed_duplicate_image_files": len(image_files),
        "logical_bytes_removed": bytes_removed,
        "training_instruction": "Run materialize_cardd_training_view.py into /content before validation or training",
    }
    (converted / "storage_manifest.json").write_text(
        json.dumps(storage_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return storage_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bronze", type=Path)
    parser.add_argument("converted", type=Path)
    args = parser.parse_args()
    print(json.dumps(slim(args.bronze, args.converted), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
