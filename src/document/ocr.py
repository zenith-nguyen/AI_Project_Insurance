"""PaddleOCR adapter normalized to the repository document schema."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Sequence

from .schema import BoundingBox, OCRToken


def _box_from_polygon(points: Sequence[Sequence[float]] | None) -> BoundingBox | None:
    if not points:
        return None
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return BoundingBox(min(xs), min(ys), max(xs), max(ys))


def normalize_paddle_output(raw: Any, page_number: int = 1) -> list[OCRToken]:
    """Normalize PaddleOCR 2.x tuples and 3.x result dictionaries."""
    tokens: list[OCRToken] = []
    if raw is None:
        return tokens
    if hasattr(raw, "json"):
        raw = raw.json
    if isinstance(raw, dict):
        payload = raw.get("res", raw)
        texts = payload.get("rec_texts", [])
        scores = payload.get("rec_scores", [])
        boxes = payload.get("rec_polys") or payload.get("dt_polys") or []
        for index, text in enumerate(texts):
            score = float(scores[index]) if index < len(scores) else 0.0
            box = _box_from_polygon(boxes[index]) if index < len(boxes) else None
            tokens.append(OCRToken(str(text), score, box, page_number))
        return tokens
    if isinstance(raw, (list, tuple)):
        # Legacy item: [polygon, (text, confidence)]. Recurse through page wrappers.
        if (
            len(raw) == 2
            and isinstance(raw[0], (list, tuple))
            and isinstance(raw[1], (list, tuple))
            and len(raw[1]) >= 2
            and isinstance(raw[1][0], str)
        ):
            return [OCRToken(str(raw[1][0]), float(raw[1][1]), _box_from_polygon(raw[0]), page_number)]
        for item in raw:
            tokens.extend(normalize_paddle_output(item, page_number))
    return tokens


class PaddleOCREngine:
    def __init__(self, lang: str = "en", **kwargs: Any) -> None:
        # PaddlePaddle 3.3.x on Windows can fail in the oneDNN/PIR executor for
        # PP-OCRv6. Keep the portable CPU path until upstream supports the
        # ArrayAttribute<DoubleAttribute> conversion used by these models.
        os.environ.setdefault("FLAGS_use_mkldnn", "0")
        kwargs.setdefault("enable_mkldnn", False)
        try:
            from paddleocr import PaddleOCR
        except ImportError as error:
            raise RuntimeError(
                "PaddleOCR is optional; install requirements-document.txt and a compatible PaddlePaddle wheel."
            ) from error
        self.model_name = "PaddleOCR"
        self.model_version = "runtime"
        self._engine = PaddleOCR(lang=lang, **kwargs)

    def predict(self, image: Path, page_number: int = 1) -> list[OCRToken]:
        if hasattr(self._engine, "predict"):
            raw = list(self._engine.predict(str(image)))
        else:
            raw = self._engine.ocr(str(image), cls=True)
        return normalize_paddle_output(raw, page_number)
