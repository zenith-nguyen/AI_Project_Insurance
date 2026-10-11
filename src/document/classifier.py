"""Document classification baselines with lazy optional model imports."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence


@dataclass(frozen=True)
class Classification:
    label: str
    confidence: float
    scores: dict[str, float]


class DocumentClassifier(Protocol):
    model_name: str
    model_version: str

    def predict(self, images: Sequence[Path]) -> list[Classification]: ...


class DiTClassifier:
    """Inference adapter for Microsoft's RVL-CDIP-fine-tuned DiT checkpoint."""

    def __init__(
        self,
        model_name: str = "microsoft/dit-base-finetuned-rvlcdip",
        revision: str = "23f8b03d130fb66bbc9a15df3c75d753e49240eb",
        device: str | None = None,
    ) -> None:
        try:
            import torch
            from transformers import AutoImageProcessor, AutoModelForImageClassification
        except ImportError as error:
            raise RuntimeError(
                "DiT requires torch and transformers; install requirements-document.txt."
            ) from error

        self.model_name = model_name
        self.model_version = revision
        self._torch = torch
        self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._processor = AutoImageProcessor.from_pretrained(model_name, revision=revision)
        self._model = AutoModelForImageClassification.from_pretrained(
            model_name, revision=revision
        ).to(self._device)
        self._model.eval()

    def predict(self, images: Sequence[Path]) -> list[Classification]:
        from PIL import Image

        loaded = []
        for path in images:
            with Image.open(path) as image:
                loaded.append(image.convert("RGB"))
        inputs = self._processor(images=loaded, return_tensors="pt")
        inputs = {name: value.to(self._device) for name, value in inputs.items()}
        with self._torch.inference_mode():
            probabilities = self._model(**inputs).logits.softmax(dim=-1).cpu()

        id2label = self._model.config.id2label
        predictions = []
        for row in probabilities:
            scores = {str(id2label[index]): float(score) for index, score in enumerate(row)}
            label = max(scores, key=scores.get)
            predictions.append(Classification(label, scores[label], scores))
        return predictions
