"""Live YOLO segmentation inference adapter with artifact integrity checks."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class YOLODamageAdapter:
    model_name = "yolov8s-seg"
    model_version = "cardd_candidate_v1"

    def __init__(
        self,
        weights: str | Path,
        *,
        expected_sha256: str,
        device: str | None = None,
        model: Any | None = None,
    ) -> None:
        self.weights = Path(weights)
        if not self.weights.is_file():
            raise FileNotFoundError(self.weights)
        actual = file_sha256(self.weights)
        if actual != expected_sha256:
            raise RuntimeError(f"YOLO checkpoint hash mismatch: expected {expected_sha256}, got {actual}")
        if model is None:
            try:
                from ultralytics import YOLO
            except ImportError as error:
                raise RuntimeError("YOLO inference requires requirements-gpu.txt.") from error
            model = YOLO(str(self.weights))
        self.model = model
        self.device = device

    def predict(self, image: str | Path, *, confidence: float = 0.25, image_size: int = 640) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {"source": str(image), "conf": confidence, "imgsz": image_size, "verbose": False}
        if self.device:
            kwargs["device"] = self.device
        result = self.model.predict(**kwargs)[0]
        names = result.names
        boxes = result.boxes
        polygons = result.masks.xy if result.masks is not None else []
        detections: list[dict[str, Any]] = []
        for index in range(len(boxes)):
            class_id = int(boxes.cls[index].item())
            box = [float(value) for value in boxes.xyxy[index].tolist()]
            polygon = polygons[index].tolist() if index < len(polygons) else None
            detections.append({
                "class_id": class_id,
                "class_name": str(names[class_id]),
                "confidence": float(boxes.conf[index].item()),
                "box_xyxy": box,
                "mask_polygon": polygon,
            })
        return detections
