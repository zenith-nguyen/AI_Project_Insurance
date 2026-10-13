"""Run the registered CarDD YOLO checkpoint on one image.

This is a deployment smoke/inference command. It does not read the locked
CarDD test split and it does not update model weights.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.common import sha256
from src.image.inference import YOLODamageAdapter
from src.registry import load_registry


DEFAULT_WEIGHTS = ROOT / "artifacts/models/damage_segmentation/cardd_candidate_v1/best.pt"


def render_overlay(image_path: Path, detections: list[dict], output_path: Path) -> None:
    image = Image.open(image_path).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    colors = ((0, 148, 136, 90), (255, 152, 0, 90), (229, 57, 53, 90), (63, 81, 181, 90))
    for index, detection in enumerate(detections):
        color = colors[index % len(colors)]
        polygon = detection.get("mask_polygon")
        if polygon:
            draw.polygon([tuple(point) for point in polygon], fill=color, outline=color[:3] + (220,))
        box = detection["box_xyxy"]
        draw.rectangle(box, outline=color[:3] + (255,), width=3)
        label = f"{detection['class_name']} {detection['confidence']:.2f}"
        text_box = draw.textbbox((box[0], box[1]), label)
        draw.rectangle(text_box, fill=(20, 32, 34, 220))
        draw.text((box[0], box[1]), label, fill=(255, 255, 255, 255))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.alpha_composite(image, overlay).convert("RGB").save(output_path, quality=95)


def run(
    image_path: Path,
    weights: Path,
    output_dir: Path,
    confidence: float,
    image_size: int,
    device: str | None,
) -> dict:
    if not image_path.is_file():
        raise FileNotFoundError(image_path)
    registry = load_registry(ROOT / "configs/model_registry.v1.yaml")
    registered = registry.modules["damage_segmentation"]
    adapter = YOLODamageAdapter(
        weights,
        expected_sha256=registered.artifact_hash,
        device=device,
    )
    detections = adapter.predict(image_path, confidence=confidence, image_size=image_size)
    output_dir.mkdir(parents=True, exist_ok=True)
    overlay_path = output_dir / f"{image_path.stem}_damage_overlay.jpg"
    report_path = output_dir / f"{image_path.stem}_damage_result.json"
    render_overlay(image_path, detections, overlay_path)
    report = {
        "schema_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "vehicle_damage_segmentation",
        "model_name": adapter.model_name,
        "model_version": adapter.model_version,
        "checkpoint_sha256": registered.artifact_hash,
        "image": str(image_path.resolve()),
        "image_sha256": sha256(image_path),
        "confidence_threshold": confidence,
        "image_size": image_size,
        "detection_count": len(detections),
        "detections": detections,
        "overlay": str(overlay_path.resolve()),
        "limitations": [
            "CarDD v1 covers crack, dent, glass shatter, lamp broken, scratch and tire flat only.",
            "A missing detection does not establish that the vehicle is undamaged.",
            "The output supports human review and is not a repair-cost estimate or fraud decision.",
        ],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "runtime/damage_inference")
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--device")
    args = parser.parse_args()
    if not 0 < args.confidence < 1:
        parser.error("--confidence must be between 0 and 1")
    report = run(
        args.image,
        args.weights,
        args.output_dir,
        args.confidence,
        args.image_size,
        args.device,
    )
    print(json.dumps({
        "status": "PASS",
        "detections": report["detection_count"],
        "overlay": report["overlay"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

