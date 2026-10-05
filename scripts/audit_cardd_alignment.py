"""Audit alignment between CarDD FiftyOne sample records and downloaded images."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def sample_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict) and isinstance(payload.get("samples"), list):
        records = payload["samples"]
    else:
        raise ValueError("samples.json must be a list or contain a top-level 'samples' list")
    if not all(isinstance(record, dict) for record in records):
        raise ValueError("Every sample record must be a JSON object")
    return records


def reference_name(record: dict[str, Any]) -> str | None:
    value = record.get("filepath")
    if not isinstance(value, str) or not value.strip():
        return None
    return Path(value.replace("\\", "/")).name


def audit(root: Path) -> dict[str, Any]:
    root = root.resolve()
    records = sample_records(json.loads((root / "samples.json").read_text(encoding="utf-8")))
    images = [path for path in (root / "data").rglob("*") if path.is_file() and path.suffix.casefold() in IMAGE_SUFFIXES]

    actual_names = Counter(path.name for path in images)
    references = [reference_name(record) for record in records]
    referenced_names = Counter(name for name in references if name is not None)
    missing_filepath_records = [index for index, name in enumerate(references) if name is None]
    missing_images = sorted(name for name in referenced_names if name not in actual_names)
    unreferenced_images = sorted(name for name in actual_names if name not in referenced_names)
    duplicate_references = {name: count for name, count in sorted(referenced_names.items()) if count > 1}
    duplicate_image_names = {name: count for name, count in sorted(actual_names.items()) if count > 1}

    return {
        "root": str(root),
        "sample_records": len(records),
        "image_files": len(images),
        "records_without_filepath": len(missing_filepath_records),
        "records_without_filepath_indices_first_50": missing_filepath_records[:50],
        "unique_referenced_filenames": len(referenced_names),
        "unique_downloaded_filenames": len(actual_names),
        "missing_referenced_images": len(missing_images),
        "missing_referenced_images_first_100": missing_images[:100],
        "unreferenced_downloaded_images": len(unreferenced_images),
        "unreferenced_downloaded_images_first_100": unreferenced_images[:100],
        "duplicate_sample_references": duplicate_references,
        "duplicate_downloaded_filenames": duplicate_image_names,
        "ready_for_conversion": not (
            missing_filepath_records
            or missing_images
            or unreferenced_images
            or duplicate_references
            or duplicate_image_names
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cardd_root", type=Path)
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    args = parser.parse_args()
    report = audit(args.cardd_root)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
