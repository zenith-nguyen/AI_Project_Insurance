"""Optional calibrated pixel-forensics adapter.

The adapter refuses to run without a calibration manifest explicitly signed off
for the target domain. This prevents a public AI-image detector from silently
becoming a production fraud rule.
"""
from __future__ import annotations

import json
from pathlib import Path


class CalibratedImageForensics:
    def __init__(self, checkpoint: str | Path, calibration: str | Path, *, device: str | None = None) -> None:
        self.checkpoint = Path(checkpoint)
        self.calibration_path = Path(calibration)
        if not self.checkpoint.exists() or not self.calibration_path.is_file():
            raise FileNotFoundError("Forensic checkpoint and calibration manifest are both required.")
        self.calibration = json.loads(self.calibration_path.read_text(encoding="utf-8"))
        required = {
            "model_name", "model_version", "positive_label", "threshold_review", "threshold_high",
            "benchmark_id", "domain", "calibrated", "validated_for_insurance",
        }
        missing = required - set(self.calibration)
        if missing:
            raise ValueError(f"Forensic calibration manifest is missing: {sorted(missing)}")
        if not self.calibration["calibrated"] or not self.calibration["validated_for_insurance"]:
            raise ValueError("Forensic model must be calibrated and validated for insurance before activation.")
        low, high = float(self.calibration["threshold_review"]), float(self.calibration["threshold_high"])
        if not 0 <= low <= high <= 1:
            raise ValueError("Forensic thresholds must satisfy 0 <= review <= high <= 1.")
        try:
            import torch
            from transformers import AutoImageProcessor, AutoModelForImageClassification
        except ImportError as error:
            raise RuntimeError("Install requirements-document.txt to activate pixel forensics.") from error
        self.torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.processor = AutoImageProcessor.from_pretrained(self.checkpoint, local_files_only=True)
        self.model = AutoModelForImageClassification.from_pretrained(self.checkpoint, local_files_only=True).to(self.device).eval()
        labels = {str(value).lower(): int(key) for key, value in self.model.config.id2label.items()}
        positive = str(self.calibration["positive_label"]).lower()
        if positive not in labels:
            raise ValueError(f"Positive label {positive!r} is absent from model config.")
        self.positive_id = labels[positive]

    def __call__(self, path: Path) -> dict:
        from PIL import Image

        with Image.open(path) as image:
            inputs = {key: value.to(self.device) for key, value in self.processor(images=image.convert("RGB"), return_tensors="pt").items()}
        with self.torch.inference_mode():
            probabilities = self.model(**inputs).logits.softmax(dim=-1)[0]
        score = float(probabilities[self.positive_id].detach().cpu())
        return {
            **{key: self.calibration[key] for key in (
                "model_name", "model_version", "threshold_review", "threshold_high",
                "benchmark_id", "domain", "calibrated",
            )},
            "score_ai": score,
        }
