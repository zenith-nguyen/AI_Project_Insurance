"""PaddleOCR adapter normalized to the repository document schema."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Sequence

from PIL import Image

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
    def __init__(
        self,
        lang: str = "en",
        *,
        profile: str = "robust",
        max_side: int | None = None,
        **kwargs: Any,
    ) -> None:
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
        if profile not in {"robust", "fast_upright"}:
            raise ValueError(f"Unknown PaddleOCR profile: {profile}")
        if max_side is not None and max_side < 640:
            raise ValueError("OCR max_side must be at least 640 pixels.")
        if profile == "fast_upright":
            kwargs.setdefault("use_doc_orientation_classify", False)
            kwargs.setdefault("use_doc_unwarping", False)
            kwargs.setdefault("use_textline_orientation", False)
        self.model_name = "PaddleOCR"
        self.profile = profile
        self.max_side = max_side
        size_label = f"-max{max_side}" if max_side else ""
        self.model_version = f"runtime-{lang}-{profile}{size_label}"
        self._engine = PaddleOCR(lang=lang, **kwargs)

    def predict(self, image: Path, page_number: int = 1) -> list[OCRToken]:
        source = Path(image)
        temporary: Path | None = None
        scale_x = scale_y = 1.0
        try:
            inference_path = source
            if self.max_side:
                with Image.open(source) as opened:
                    width, height = opened.size
                    if max(width, height) > self.max_side:
                        resized = opened.convert("RGB")
                        resized.thumbnail((self.max_side, self.max_side), Image.Resampling.LANCZOS)
                        handle = tempfile.NamedTemporaryFile(prefix="insurance-ocr-", suffix=".png", delete=False)
                        handle.close()
                        temporary = Path(handle.name)
                        resized.save(temporary, optimize=True)
                        inference_path = temporary
                        scale_x = width / resized.width
                        scale_y = height / resized.height
            if hasattr(self._engine, "predict"):
                raw = list(self._engine.predict(str(inference_path)))
            else:
                raw = self._engine.ocr(str(inference_path), cls=True)
            tokens = normalize_paddle_output(raw, page_number)
            if scale_x == 1.0 and scale_y == 1.0:
                return tokens
            return [
                OCRToken(
                    token.text,
                    token.confidence,
                    (
                        BoundingBox(
                            token.bbox.x1 * scale_x, token.bbox.y1 * scale_y,
                            token.bbox.x2 * scale_x, token.bbox.y2 * scale_y,
                        )
                        if token.bbox else None
                    ),
                    token.page_number,
                )
                for token in tokens
            ]
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
