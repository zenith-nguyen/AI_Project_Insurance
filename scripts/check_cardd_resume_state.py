"""Inspect whether a CarDD project can resume without rewriting any files."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return [
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.casefold() in IMAGE_SUFFIXES
    ]


def inspect(project: Path, conversion_project: Path | None = None) -> dict[str, Any]:
    project = project.resolve()
    conversion_project = (conversion_project or project).resolve()
    bronze = project / "data/bronze/layerA_cardd"
    processed = conversion_project / "data/processed/cardd_yolo_v1"
    samples_path = bronze / "samples.json"
    report_path = processed / "conversion_report.json"
    manifest_path = processed / "split_manifest.jsonl"

    payload = json.loads(samples_path.read_text(encoding="utf-8")) if samples_path.is_file() else None
    records = payload if isinstance(payload, list) else (payload or {}).get("samples", [])
    referenced = [
        Path(str(record.get("filepath", "")).replace("\\", "/")).name
        for record in records
        if record.get("filepath")
    ]
    bronze_images = image_files(bronze / "data")
    bronze_names = Counter(path.name for path in bronze_images)
    referenced_names = Counter(referenced)
    missing_bronze = sorted(referenced_names.keys() - bronze_names.keys())
    unreferenced_bronze = sorted(bronze_names.keys() - referenced_names.keys())

    conversion_report = (
        json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else None
    )
    manifest_rows = []
    if manifest_path.is_file():
        manifest_rows = [
            json.loads(line)
            for line in manifest_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    labels_by_split: Counter[str] = Counter()
    for split in ("train", "val", "test"):
        labels_by_split[split] = len(list((processed / "labels" / split).glob("*.txt")))
    images_by_split: Counter[str] = Counter()
    for split in ("train", "val", "test"):
        images_by_split[split] = len(image_files(processed / "images" / split))

    missing_labels = []
    for row in manifest_rows:
        image_name = row.get("image", "")
        split = row.get("split", "")
        label = processed / "labels" / split / f"{Path(image_name).stem}.txt"
        if not label.is_file():
            missing_labels.append(image_name)

    expected = int(conversion_report.get("images", 0)) if conversion_report else 0
    reported_splits = conversion_report.get("split_images", {}) if conversion_report else {}
    manifest_splits = Counter(str(row.get("split")) for row in manifest_rows)
    bronze_ready = bool(records) and (
        len(records) == len(bronze_images) == len(referenced_names)
        and not missing_bronze
        and not unreferenced_bronze
        and max(bronze_names.values(), default=0) == 1
    )
    metadata_ready = bool(conversion_report and manifest_rows) and (
        expected == len(manifest_rows)
        and not missing_labels
        and set(row.get("image") for row in manifest_rows) <= set(bronze_names)
        and dict(manifest_splits) == reported_splits
        and conversion_report.get("samples_json_sha256") == (
            sha256(samples_path) if samples_path.is_file() else None
        )
    )
    persistent_image_count = sum(images_by_split.values())

    return {
        "project": str(project),
        "conversion_project": str(conversion_project),
        "bronze": {
            "samples_json_exists": samples_path.is_file(),
            "samples_json_sha256": sha256(samples_path) if samples_path.is_file() else None,
            "sample_records": len(records),
            "image_files": len(bronze_images),
            "missing_referenced_images": missing_bronze[:100],
            "unreferenced_images": unreferenced_bronze[:100],
            "ready": bronze_ready,
        },
        "conversion": {
            "report_exists": report_path.is_file(),
            "manifest_exists": manifest_path.is_file(),
            "reported_images": expected,
            "reported_split_images": reported_splits,
            "manifest_rows": len(manifest_rows),
            "manifest_split_images": dict(manifest_splits),
            "label_files": dict(labels_by_split),
            "missing_labels": missing_labels[:100],
            "persistent_image_files": dict(images_by_split),
            "image_materialization_modes": (
                conversion_report.get("image_materialization_modes", {})
                if conversion_report else {}
            ),
            "metadata_ready": metadata_ready,
        },
        "resume": {
            "ready_to_materialize": bronze_ready and metadata_ready,
            "duplicate_processed_images_present": persistent_image_count > 0,
            "safe_cleanup_candidate": (
                bronze_ready and metadata_ready and persistent_image_count == expected
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="AI_Project_Insurance root")
    parser.add_argument(
        "--conversion-project",
        type=Path,
        help="Optional separate project root containing processed labels/report",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON output; omit on a full Drive")
    args = parser.parse_args()
    result = inspect(args.project, args.conversion_project)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
