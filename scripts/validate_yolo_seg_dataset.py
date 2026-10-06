"""Validate a converted Ultralytics instance-segmentation dataset before training."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
import yaml


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def polygon_area(points: np.ndarray) -> float:
    x, y = points[:, 0], points[:, 1]
    return float(abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))) / 2)


def validate(dataset: Path) -> dict:
    config = yaml.safe_load((dataset / "data.yaml").read_text(encoding="utf-8"))
    class_count = len(config["names"])
    report = {"splits": {}, "errors": []}
    real_images_by_split: dict[str, set[str]] = {}
    for split in ("train", "val", "test"):
        image_dir = dataset / "images" / split
        label_dir = dataset / "labels" / split
        images = sorted(path for path in image_dir.iterdir() if path.suffix.casefold() in IMAGE_SUFFIXES)
        labels = sorted(label_dir.glob("*.txt"))
        image_stems, label_stems = {path.stem for path in images}, {path.stem for path in labels}
        missing_labels = sorted(image_stems - label_stems)
        orphan_labels = sorted(label_stems - image_stems)
        class_instances: Counter[int] = Counter()
        invalid_rows = 0
        for label_path in labels:
            for line_number, line in enumerate(label_path.read_text(encoding="utf-8").splitlines(), start=1):
                try:
                    values = [float(value) for value in line.split()]
                    class_id = int(values[0])
                    coordinates = np.asarray(values[1:], dtype=float)
                    points = coordinates.reshape(-1, 2)
                    valid = (
                        values[0] == class_id
                        and 0 <= class_id < class_count
                        and len(points) >= 3
                        and np.isfinite(points).all()
                        and (points >= 0).all()
                        and (points <= 1).all()
                        and polygon_area(points) > 0
                    )
                    if not valid:
                        raise ValueError("invalid class or polygon")
                    class_instances[class_id] += 1
                except Exception as error:
                    invalid_rows += 1
                    if len(report["errors"]) < 100:
                        report["errors"].append(f"{label_path}:{line_number}: {error}")
        real_images_by_split[split] = {str(path.resolve()) for path in images}
        report["splits"][split] = {
            "images": len(images),
            "labels": len(labels),
            "instances": sum(class_instances.values()),
            "class_instances": {str(key): value for key, value in sorted(class_instances.items())},
            "missing_labels": missing_labels,
            "orphan_labels": orphan_labels,
            "invalid_rows": invalid_rows,
        }
    overlaps = {}
    for left, right in (("train", "val"), ("train", "test"), ("val", "test")):
        overlaps[f"{left}_{right}"] = len(real_images_by_split[left] & real_images_by_split[right])
    report["resolved_image_overlaps"] = overlaps
    report["valid"] = not report["errors"] and not any(
        split["missing_labels"] or split["orphan_labels"] or split["invalid_rows"]
        for split in report["splits"].values()
    ) and not any(overlaps.values())
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = validate(args.dataset.resolve())
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if not report["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
