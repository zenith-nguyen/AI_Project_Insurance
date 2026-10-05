"""Inspect a downloaded CarDD FiftyOne dataset without assuming COCO format."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

import yaml
from pypdf import PdfReader


REQUIRED_FILES = ("fiftyone.yml", "samples.json", "metadata.json")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
GEOMETRY_KEYS = {"bounding_box", "mask", "points", "polylines", "segmentation"}


def walk(value: Any, path: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], Any]]:
    """Yield every node with its JSON path."""
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, path + (str(key),))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, path + (str(index),))


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


def annotation_summary(records: list[dict[str, Any]]) -> tuple[list[str], list[str], dict[str, int]]:
    labels: set[str] = set()
    annotation_types: set[str] = set()
    geometry_counts: Counter[str] = Counter()
    for record in records:
        for path, node in walk(record):
            if not isinstance(node, dict):
                continue
            cls = node.get("_cls")
            if isinstance(cls, str) and any(token in cls.casefold() for token in ("detection", "polyline", "segment", "keypoint", "classification")):
                annotation_types.add(cls)
            geometry = GEOMETRY_KEYS.intersection(node)
            for key in geometry:
                geometry_counts[key] += 1
            label = node.get("label")
            path_text = "/".join(path).casefold()
            looks_like_annotation = bool(geometry) or any(token in path_text for token in ("detection", "ground_truth", "polyline", "segment"))
            if isinstance(label, str) and label.strip() and looks_like_annotation:
                labels.add(label.strip())
    return sorted(labels), sorted(annotation_types), dict(sorted(geometry_counts.items()))


def find_license(root: Path) -> Path:
    matches = [path for path in root.rglob("*.pdf") if path.name.casefold() == "cardd_license.pdf"]
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected exactly one CarDD_license.pdf under {root}; found {len(matches)}")
    return matches[0]


def read_license(path: Path) -> str:
    pages = [(page.extract_text() or "").strip() for page in PdfReader(path).pages]
    text = "\n\n".join(page for page in pages if page).strip()
    if not text:
        raise ValueError(f"No extractable text found in {path}; the PDF may be image-only")
    return text


def inspect_cardd(root: Path) -> dict[str, Any]:
    root = root.resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)
    missing = [name for name in REQUIRED_FILES if not (root / name).is_file()]
    if not (root / "data").is_dir():
        missing.append("data/")
    if missing:
        raise FileNotFoundError(f"Missing expected FiftyOne paths under {root}: {', '.join(missing)}")

    fiftyone_config = yaml.safe_load((root / "fiftyone.yml").read_text(encoding="utf-8")) or {}
    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    samples_payload = json.loads((root / "samples.json").read_text(encoding="utf-8"))
    records = sample_records(samples_payload)
    classes, annotation_types, geometry_counts = annotation_summary(records)
    images = sorted(path for path in (root / "data").rglob("*") if path.is_file() and path.suffix.casefold() in IMAGE_SUFFIXES)
    suffix_counts = Counter(path.suffix.casefold() for path in images)
    license_path = find_license(root)
    license_text = read_license(license_path)

    dataset_type = fiftyone_config.get("type") or fiftyone_config.get("dataset_type") or fiftyone_config.get("format")
    result = {
        "root": str(root),
        "image_count": len(images),
        "image_suffix_counts": dict(sorted(suffix_counts.items())),
        "sample_record_count": len(records),
        "image_sample_count_match": len(images) == len(records),
        "annotation_storage": "FiftyOne samples.json",
        "declared_dataset_type": dataset_type,
        "annotation_types_found": annotation_types,
        "geometry_fields_found": geometry_counts,
        "damage_classes_found": classes,
        "damage_class_count": len(classes),
        "metadata_top_level_keys": sorted(metadata) if isinstance(metadata, dict) else [],
        "license_file": str(license_path.relative_to(root)),
        "license_text": license_text,
    }
    return result


def print_report(report: dict[str, Any]) -> None:
    print(f"CarDD root: {report['root']}")
    print(f"Total images: {report['image_count']} {report['image_suffix_counts']}")
    print(f"FiftyOne sample records: {report['sample_record_count']}")
    print(f"Image/sample counts match: {report['image_sample_count_match']}")
    print(f"Declared dataset type: {report['declared_dataset_type']}")
    print(f"Annotation storage actually present: {report['annotation_storage']}")
    print(f"Annotation types found: {report['annotation_types_found']}")
    print(f"Geometry fields found: {report['geometry_fields_found']}")
    print(f"Damage classes found ({report['damage_class_count']}): {report['damage_classes_found']}")
    if report["damage_class_count"] != 6:
        print("WARNING: Expected 6 damage classes from project context; actual annotations differ or were not fully detected.")
    print(f"License file: {report['license_file']}")
    print("\n--- CarDD license text ---\n")
    print(report["license_text"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cardd_root", type=Path, help="Folder containing fiftyone.yml, samples.json, metadata.json, data/, and CarDD_license.pdf")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON instead of the text report")
    args = parser.parse_args()
    inspection = inspect_cardd(args.cardd_root)
    if args.json:
        print(json.dumps(inspection, ensure_ascii=False, indent=2))
    else:
        print_report(inspection)
