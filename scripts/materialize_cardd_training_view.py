"""Create an ephemeral local YOLO view backed by Bronze images and stored labels."""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

import yaml


def materialize(bronze: Path, converted: Path, target: Path) -> dict:
    bronze, converted, target = bronze.resolve(), converted.resolve(), target.resolve()
    if target.exists():
        raise FileExistsError(f"Target already exists: {target}")
    report = json.loads((converted / "conversion_report.json").read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in (converted / "split_manifest.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    if len(rows) != int(report["images"]):
        raise ValueError("Split manifest count does not match conversion report")
    building = target.with_name(target.name + ".building")
    if building.exists():
        raise FileExistsError(f"Stale materialization directory exists: {building}")
    link_counts = {"images": 0, "labels": 0}
    building.mkdir(parents=True)
    try:
        for index, row in enumerate(rows, start=1):
            image_name, split = row["image"], row["split"]
            source_image = bronze / "data" / image_name
            source_label = converted / "labels" / split / f"{Path(image_name).stem}.txt"
            if not source_image.is_file() or not source_label.is_file():
                raise FileNotFoundError(f"Missing source image or label for {image_name}")
            image_link = building / "images" / split / image_name
            label_link = building / "labels" / split / source_label.name
            image_link.parent.mkdir(parents=True, exist_ok=True)
            label_link.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(source_image, image_link)
            os.symlink(source_label, label_link)
            link_counts["images"] += 1
            link_counts["labels"] += 1
            if index % 500 == 0 or index == len(rows):
                print(f"Training view links: {index}/{len(rows)}", flush=True)
        data_yaml = {
            "path": str(target),
            "train": "images/train",
            "val": "images/val",
            "test": "images/test",
            "names": {index: name for index, name in enumerate(report["classes"])},
        }
        (building / "data.yaml").write_text(
            yaml.safe_dump(data_yaml, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )
        building.replace(target)
    except Exception:
        shutil.rmtree(building, ignore_errors=True)
        raise
    return {
        "target": str(target),
        "source_bronze": str(bronze),
        "source_labels": str(converted / "labels"),
        "image_links": link_counts["images"],
        "label_links": link_counts["labels"],
        "persistent_image_bytes_added": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bronze", type=Path)
    parser.add_argument("converted", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    print(json.dumps(materialize(args.bronze, args.converted, args.target), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
