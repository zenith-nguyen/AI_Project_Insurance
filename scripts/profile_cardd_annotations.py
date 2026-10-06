"""Profile CarDD FiftyOne annotation schema before writing a converter."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterator


def walk(value: Any, path: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, path + (str(key),))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, path + (str(index),))


def path_pattern(path: tuple[str, ...]) -> str:
    return "/".join("[]" if part.isdigit() else part for part in path)


def mask_signature(mask: Any) -> dict[str, Any]:
    if isinstance(mask, list):
        rows = len(mask)
        nested = bool(mask) and isinstance(mask[0], list)
        widths = [len(row) for row in mask if isinstance(row, list)] if nested else []
        return {
            "type": "list",
            "rows": rows,
            "columns_min": min(widths) if widths else None,
            "columns_max": max(widths) if widths else None,
        }
    if isinstance(mask, dict):
        return {"type": "dict", "keys": sorted(mask)}
    if isinstance(mask, str):
        return {"type": "string", "length": len(mask), "prefix": mask[:40]}
    return {"type": type(mask).__name__}


def profile(root: Path) -> dict[str, Any]:
    payload = json.loads((root / "samples.json").read_text(encoding="utf-8"))
    records = payload if isinstance(payload, list) else payload.get("samples")
    if not isinstance(records, list) or not all(isinstance(record, dict) for record in records):
        raise ValueError("samples.json does not contain a valid sample list")

    sample_keys: Counter[str] = Counter()
    tags: Counter[str] = Counter()
    container_paths: Counter[str] = Counter()
    detection_paths: Counter[str] = Counter()
    class_counts: Counter[str] = Counter()
    mask_signatures: Counter[str] = Counter()
    example_detections: dict[str, dict[str, Any]] = {}
    annotated_samples = 0
    detections_with_bbox = 0
    detections_with_mask = 0
    invalid_bboxes = 0

    for record in records:
        sample_keys.update(record)
        if isinstance(record.get("tags"), list):
            tags.update(str(tag) for tag in record["tags"])
        sample_has_detection = False
        for path, node in walk(record):
            if not isinstance(node, dict):
                continue
            cls = str(node.get("_cls", "")).rsplit(".", 1)[-1]
            if cls == "Detections":
                container_paths[path_pattern(path)] += 1
            if cls != "Detection" and not (
                isinstance(node.get("label"), str)
                and ("bounding_box" in node or "mask" in node)
            ):
                continue

            sample_has_detection = True
            detection_paths[path_pattern(path)] += 1
            label = str(node.get("label", "__MISSING_LABEL__"))
            class_counts[label] += 1

            bbox = node.get("bounding_box")
            if bbox is not None:
                detections_with_bbox += 1
                valid = (
                    isinstance(bbox, list)
                    and len(bbox) == 4
                    and all(isinstance(value, (int, float)) for value in bbox)
                    and bbox[0] >= 0
                    and bbox[1] >= 0
                    and bbox[2] > 0
                    and bbox[3] > 0
                    and bbox[0] + bbox[2] <= 1.000001
                    and bbox[1] + bbox[3] <= 1.000001
                )
                invalid_bboxes += int(not valid)

            if "mask" in node:
                detections_with_mask += 1
                signature = mask_signature(node["mask"])
                mask_signatures[json.dumps(signature, sort_keys=True)] += 1
                example_detections.setdefault(
                    label,
                    {
                        "path": path_pattern(path),
                        "keys": sorted(node),
                        "bounding_box": bbox,
                        "mask_signature": signature,
                    },
                )
        annotated_samples += int(sample_has_detection)

    return {
        "sample_records": len(records),
        "annotated_samples": annotated_samples,
        "unannotated_samples": len(records) - annotated_samples,
        "sample_top_level_key_counts": dict(sorted(sample_keys.items())),
        "tag_counts": dict(sorted(tags.items())),
        "annotation_container_paths": dict(sorted(container_paths.items())),
        "detection_paths": dict(sorted(detection_paths.items())),
        "class_detection_counts": dict(sorted(class_counts.items())),
        "total_detection_objects": sum(class_counts.values()),
        "detections_with_bbox": detections_with_bbox,
        "detections_with_mask": detections_with_mask,
        "invalid_normalized_bboxes": invalid_bboxes,
        "mask_signatures": {
            signature: count for signature, count in sorted(mask_signatures.items())
        },
        "example_detection_by_class": example_detections,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cardd_root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = profile(args.cardd_root.resolve())
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
