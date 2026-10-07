"""Create an ephemeral local YOLO view backed by Bronze images and stored labels."""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

import yaml


def materialize(
    bronze: Path,
    converted: Path,
    target: Path,
    image_mode: str = "symlink",
) -> dict:
    bronze, converted, target = bronze.resolve(), converted.resolve(), target.resolve()
    if image_mode not in {"symlink", "copy"}:
        raise ValueError(f"Unsupported image mode: {image_mode}")
    if image_mode == "copy" and str(target).startswith("/content/drive/"):
        raise ValueError("Refusing to copy a training view into persistent Google Drive storage")
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
    file_counts = {"images": 0, "labels": 0}
    image_bytes = 0
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
            if image_mode == "copy":
                # Google Drive FUSE may reject metadata operations used by copy2().
                # Training only needs byte-identical content in ephemeral /content.
                shutil.copyfile(source_image, image_link)
                shutil.copyfile(source_label, label_link)
                image_bytes += source_image.stat().st_size
            else:
                os.symlink(source_image, image_link)
                os.symlink(source_label, label_link)
            file_counts["images"] += 1
            file_counts["labels"] += 1
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
    except BaseException:
        # Also clean up after an interactive interruption such as Ctrl+C.
        shutil.rmtree(building, ignore_errors=True)
        raise
    return {
        "target": str(target),
        "source_bronze": str(bronze),
        "source_labels": str(converted / "labels"),
        "image_mode": image_mode,
        "image_files": file_counts["images"],
        "label_files": file_counts["labels"],
        "image_bytes_materialized": image_bytes,
        "persistent_image_bytes_added": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bronze", type=Path)
    parser.add_argument("converted", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument(
        "--image-mode",
        choices=("symlink", "copy"),
        default="symlink",
        help="Use copy for faster Colab training in ephemeral /content storage",
    )
    args = parser.parse_args()
    print(json.dumps(
        materialize(args.bronze, args.converted, args.target, args.image_mode),
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
