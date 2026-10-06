"""Evaluate a frozen YOLO segmentation checkpoint on val or, explicitly, test."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def plain(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def metric_group(group: Any) -> dict[str, Any]:
    return {
        "map50_95": float(group.map),
        "map50": float(group.map50),
        "map75": float(group.map75),
        "per_class_map50_95": plain(group.maps),
    }


def evaluate(
    weights: Path,
    data_yaml: Path,
    output: Path,
    *,
    split: str = "val",
    project: Path,
    name: str,
    image_size: int = 640,
    batch: int = 8,
    device: str = "0",
    allow_test: bool = False,
) -> dict[str, Any]:
    if split not in {"val", "test"}:
        raise ValueError("split must be val or test")
    if split == "test" and not allow_test:
        raise PermissionError("Test evaluation requires --allow-test after model selection is frozen")
    for path in (weights, data_yaml):
        if not path.is_file():
            raise FileNotFoundError(path)
    from ultralytics import YOLO

    model = YOLO(str(weights))
    metrics = model.val(
        data=str(data_yaml),
        split=split,
        imgsz=image_size,
        batch=batch,
        device=device,
        project=str(project),
        name=name,
        plots=True,
        verbose=True,
        exist_ok=False,
    )
    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "weights": str(weights.resolve()),
        "data": str(data_yaml.resolve()),
        "split": split,
        "image_size": image_size,
        "class_names": plain(getattr(metrics, "names", {})),
        "box": metric_group(metrics.box),
        "mask": metric_group(metrics.seg),
        "results_dict": plain(metrics.results_dict),
        "speed_ms_per_image": plain(metrics.speed),
        "run_directory": str(Path(metrics.save_dir).resolve()),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", choices=("val", "test"), default="val")
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default="0")
    parser.add_argument("--allow-test", action="store_true")
    args = parser.parse_args()
    evaluate(
        args.weights,
        args.data,
        args.output,
        split=args.split,
        project=args.project,
        name=args.name,
        image_size=args.imgsz,
        batch=args.batch,
        device=args.device,
        allow_test=args.allow_test,
    )


if __name__ == "__main__":
    main()
