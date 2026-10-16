"""Lazy live document pipeline backed by the registered DiT/OCR/LayoutLMv3 models."""
from __future__ import annotations

import hashlib
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock, Thread
from typing import Callable

from .classifier import DiTClassifier
from .kie import HybridKIE, LayoutLMv3KIE
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

    pipeline_version = "dit-paddleocr-layoutlmv3-hybrid-v2"

    def __init__(self, checkpoint: str | Path, *, expected_tree_hash: str, device: str | None = None) -> None:
        self.checkpoint = Path(checkpoint)
        if not self.checkpoint.is_dir():
            raise FileNotFoundError(self.checkpoint)
        actual = tree_hash(self.checkpoint)
        if actual != expected_tree_hash:
            raise RuntimeError(f"LayoutLMv3 checkpoint hash mismatch: expected {expected_tree_hash}, got {actual}")
        self.expected_tree_hash = expected_tree_hash
        self.device = device
        self._pipeline = None
        self._pipeline_lock = Lock()
        self._status_lock = Lock()
        self._warmup_status = "not_started"
        self._warmup_started_at: str | None = None
        self._warmup_finished_at: str | None = None
        self._warmup_error: str | None = None

    @property
    def cache_version(self) -> str:
        profile = os.getenv("INSURANCE_OCR_PROFILE", "robust")
        max_side = os.getenv("INSURANCE_OCR_MAX_SIDE", "").strip() or "original"
        lang = os.getenv("INSURANCE_OCR_LANG", "en")
        return f"{self.pipeline_version}:{self.expected_tree_hash}:{lang}:{profile}:{max_side}"

    def cache_key(self, evidence_sha256: str) -> str:
        return hashlib.sha256(f"{evidence_sha256}:{self.cache_version}".encode()).hexdigest()

    def _get_pipeline(self) -> DocumentPipeline:
        if self._pipeline is not None:
            return self._pipeline
        with self._pipeline_lock:
            if self._pipeline is None:
                ocr_profile = os.getenv("INSURANCE_OCR_PROFILE", "robust")
                max_side_value = os.getenv("INSURANCE_OCR_MAX_SIDE", "").strip()
                max_side = int(max_side_value) if max_side_value else None
                layout_kie = LayoutLMv3KIE(str(self.checkpoint), device=self.device)
                self._pipeline = DocumentPipeline(
                    DiTClassifier(device=self.device),
                    PaddleOCREngine(
                        lang=os.getenv("INSURANCE_OCR_LANG", "en"),
                        profile=ocr_profile,
                        max_side=max_side,
                    ),
                    HybridKIE(layout_kie),
                )
        return self._pipeline

    def warmup(self) -> None:
        with self._status_lock:
            if self._warmup_status in {"warming", "ready"}:
                return
            self._warmup_status = "warming"
            self._warmup_started_at = datetime.now(timezone.utc).isoformat()
            self._warmup_error = None
        try:
            self._get_pipeline()
        except Exception as error:
            with self._status_lock:
                self._warmup_status = "error"
                self._warmup_error = f"{type(error).__name__}: {error}"
                self._warmup_finished_at = datetime.now(timezone.utc).isoformat()
            return
        with self._status_lock:
            self._warmup_status = "ready"
            self._warmup_finished_at = datetime.now(timezone.utc).isoformat()

    def start_warmup(self) -> None:
        with self._status_lock:
            if self._warmup_status != "not_started":
                return
            self._warmup_status = "scheduled"
        Thread(target=self.warmup, name="document-model-warmup", daemon=True).start()

    def readiness(self) -> dict[str, str | None]:
        with self._status_lock:
            status = self._warmup_status
            if self._pipeline is not None:
                status = "ready"
            return {
                "status": status,
                "started_at": self._warmup_started_at,
                "finished_at": self._warmup_finished_at,
                "error": None if status == "ready" else self._warmup_error,
            }

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

    def read_image_text(self, path: str | Path):
        """Reuse the already loaded local OCR engine for a vehicle image.

        The caller is responsible for applying a domain-specific parser.  This
        avoids loading a second OCR stack solely for plate candidates.
        """
        return self._get_pipeline().ocr.predict(Path(path))
