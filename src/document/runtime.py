"""Lazy live document pipeline backed by the registered DiT/OCR/LayoutLMv3 models."""
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Callable

from .classifier import DiTClassifier
from .kie import LayoutLMv3KIE
from .ocr import PaddleOCREngine
from .pipeline import DocumentPipeline
from .schema import DocumentResult


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(path for path in root.rglob("*") if path.is_file())
    if not files:
        raise ValueError(f"Checkpoint directory is empty: {root}")
    for path in files:
        digest.update(str(path.relative_to(root)).encode())
        digest.update(bytes.fromhex(_file_hash(path)))
    return digest.hexdigest()


class DocumentRuntimeAdapter:
    """Load expensive document models only when the first document is analyzed."""

    def __init__(self, checkpoint: str | Path, *, expected_tree_hash: str, device: str | None = None) -> None:
        self.checkpoint = Path(checkpoint)
        if not self.checkpoint.is_dir():
            raise FileNotFoundError(self.checkpoint)
        actual = tree_hash(self.checkpoint)
        if actual != expected_tree_hash:
            raise RuntimeError(f"LayoutLMv3 checkpoint hash mismatch: expected {expected_tree_hash}, got {actual}")
        self.device = device
        self._pipeline = None

    def _get_pipeline(self) -> DocumentPipeline:
        if self._pipeline is None:
            self._pipeline = DocumentPipeline(
                DiTClassifier(device=self.device),
                PaddleOCREngine(lang="en"),
                LayoutLMv3KIE(str(self.checkpoint), device=self.device),
            )
        return self._pipeline

    @staticmethod
    def _first_page(path: Path, output: Path) -> Path:
        if path.suffix.lower() != ".pdf":
            return path
        try:
            import pypdfium2 as pdfium
        except ImportError as error:
            raise RuntimeError("PDF inference requires pypdfium2.") from error
        document = pdfium.PdfDocument(str(path))
        if len(document) == 0:
            raise ValueError("PDF contains no pages.")
        page = document[0]
        page.render(scale=2).to_pil().convert("RGB").save(output, format="PNG")
        return output

    def process(
        self,
        path: str | Path,
        claim_id: str,
        document_id: str,
        progress: Callable[[str], None] | None = None,
    ) -> DocumentResult:
        source = Path(path)
        with tempfile.TemporaryDirectory(prefix="insurance-document-") as directory:
            image = self._first_page(source, Path(directory) / "page-1.png")
            return self._get_pipeline().process(image, claim_id, document_id, progress=progress)
