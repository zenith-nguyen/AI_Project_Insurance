"""Train a reproducible CarDD instance-segmentation baseline on GPU."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def train(
    data_yaml: Path,
    project: Path,
    *,
    name: str = "cardd_yolov8n_seg_baseline_v1",
    model_weights: str = "yolov8n-seg.pt",
    epochs: int = 100,
    image_size: int = 640,
    batch: int = 8,
    patience: int = 20,
    workers: int = 2,
    seed: int = 20261007,
    device: str = "0",
    fraction: float = 1.0,
    save_period: int = 10,
    resume_checkpoint: Path | None = None,
) -> Any:
    if not data_yaml.is_file():
        raise FileNotFoundError(f"Image training requires a real data YAML: {data_yaml}")
    if not 0 < fraction <= 1:
        raise ValueError("fraction must be in (0, 1]")
    from ultralytics import YOLO

    if resume_checkpoint is not None:
        if not resume_checkpoint.is_file():
            raise FileNotFoundError(resume_checkpoint)
        model = YOLO(str(resume_checkpoint))
        return model.train(resume=True)

    project.mkdir(parents=True, exist_ok=True)
    run_dir = project / name
    if run_dir.exists():
        raise FileExistsError(
            f"Run directory already exists: {run_dir}. Use a new name or --resume-checkpoint."
        )
    model = YOLO(model_weights)
    settings = {
        "data": str(data_yaml.resolve()),
        "project": str(project.resolve()),
        "name": name,
        "epochs": epochs,
        "imgsz": image_size,
        "batch": batch,
        "patience": patience,
        "workers": workers,
        "seed": seed,
        "deterministic": True,
        "device": device,
        "fraction": fraction,
        "save_period": save_period,
        "cache": False,
        "amp": True,
        "plots": True,
        "exist_ok": False,
        "verbose": True,
    }
    results = model.train(**settings)
    actual_run_dir = Path(getattr(results, "save_dir", model.trainer.save_dir))
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "CarDD research baseline; model selection uses validation only",
        "test_split_used": False,
        "model_weights": model_weights,
        "settings": settings,
        "environment": {
            "python": platform.python_version(),
            "ultralytics": importlib.metadata.version("ultralytics"),
            "torch": importlib.metadata.version("torch"),
        },
        "best_checkpoint": str((actual_run_dir / "weights/best.pt").resolve()),
        "last_checkpoint": str((actual_run_dir / "weights/last.pt").resolve()),
    }
    (actual_run_dir / "training_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--name", default="cardd_yolov8n_seg_baseline_v1")
    parser.add_argument("--model", default="yolov8n-seg.pt")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20261007)
    parser.add_argument("--device", default="0")
    parser.add_argument("--fraction", type=float, default=1.0)
    parser.add_argument("--save-period", type=int, default=10)
    parser.add_argument("--resume-checkpoint", type=Path)
    args = parser.parse_args()
    train(
        args.data,
        args.project,
        name=args.name,
        model_weights=args.model,
        epochs=args.epochs,
        image_size=args.imgsz,
        batch=args.batch,
        patience=args.patience,
        workers=args.workers,
        seed=args.seed,
        device=args.device,
        fraction=args.fraction,
        save_period=args.save_period,
        resume_checkpoint=args.resume_checkpoint,
    )


if __name__ == "__main__":
    main()
