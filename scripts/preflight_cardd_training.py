"""Fail-fast checks for a local CarDD YOLO training view and CUDA runtime."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import yaml


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def inspect(data_yaml: Path, output_root: Path, require_cuda: bool = True) -> dict:
    import torch

    data_yaml = data_yaml.resolve()
    config = yaml.safe_load(data_yaml.read_text(encoding="utf-8"))
    dataset_root = Path(config["path"]).resolve()
    splits = {}
    for split in ("train", "val", "test"):
        image_dir = dataset_root / config[split]
        label_dir = dataset_root / str(config[split]).replace("images/", "labels/", 1)
        images = [
            path for path in image_dir.iterdir()
            if path.is_file() and path.suffix.casefold() in IMAGE_SUFFIXES
        ]
        labels = list(label_dir.glob("*.txt"))
        splits[split] = {"images": len(images), "labels": len(labels)}
    local_disk = shutil.disk_usage(dataset_root)
    output_root.mkdir(parents=True, exist_ok=True)
    output_disk = shutil.disk_usage(output_root)
    cuda_available = torch.cuda.is_available()
    report = {
        "data_yaml": str(data_yaml),
        "dataset_root": str(dataset_root),
        "splits": splits,
        "classes": config["names"],
        "cuda_available": cuda_available,
        "cuda_device_count": torch.cuda.device_count(),
        "cuda_device_name": torch.cuda.get_device_name(0) if cuda_available else None,
        "cuda_memory_gb": (
            round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2)
            if cuda_available else None
        ),
        "local_free_gb": round(local_disk.free / 1024**3, 2),
        "output_free_gb": round(output_disk.free / 1024**3, 2),
    }
    errors = []
    if require_cuda and not cuda_available:
        errors.append("CUDA GPU is required for this training protocol")
    for split, counts in splits.items():
        if counts["images"] == 0 or counts["images"] != counts["labels"]:
            errors.append(f"{split} image/label count is invalid: {counts}")
    if local_disk.free < 5 * 1024**3:
        errors.append("Less than 5 GB remains in ephemeral local storage")
    report["errors"] = errors
    report["ready"] = not errors
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--allow-cpu", action="store_true")
    args = parser.parse_args()
    report = inspect(args.data, args.output_root, require_cuda=not args.allow_cpu)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
