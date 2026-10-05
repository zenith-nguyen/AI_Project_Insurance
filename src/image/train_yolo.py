"""GPU branch for separately labeled, Ultralytics-formatted damage data."""
from __future__ import annotations

import argparse
from pathlib import Path


def train(data_yaml: Path, project: Path, epochs: int = 50, image_size: int = 640, seed: int = 42, device: str = "auto"):
    if not data_yaml.is_file():
        raise FileNotFoundError(f"Image training requires a real data YAML: {data_yaml}")
    from ultralytics import YOLO

    model = YOLO("yolov8n-seg.pt")
    return model.train(data=str(data_yaml), project=str(project), name="cardd_seg_v1", epochs=epochs, imgsz=image_size, seed=seed, device=device, exist_ok=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--project", type=Path, default=Path("artifacts/image"))
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()
    train(args.data, args.project, args.epochs, args.imgsz, device=args.device)
