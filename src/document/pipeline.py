"""End-to-end document inference orchestration independent from notebooks."""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from .schema import DocumentResult


class DocumentPipeline:
    def __init__(self, classifier, ocr, kie) -> None:
        self.classifier = classifier
        self.ocr = ocr
        self.kie = kie

    def process(self, image: Path, claim_id: str, document_id: str) -> DocumentResult:
        classification = self.classifier.predict([image])[0]
        tokens = self.ocr.predict(image)
        fields = self.kie.extract(tokens, image=image)
        warnings = []
        if not tokens:
            warnings.append("ocr_no_text")
        if classification.confidence < 0.5:
            warnings.append("low_document_type_confidence")
        return DocumentResult(
            claim_id=claim_id,
            document_id=document_id,
            document_type=classification.label,
            document_type_confidence=classification.confidence,
            tokens=tokens,
            fields=fields,
            model_versions={
                "classifier": f"{self.classifier.model_name}@{self.classifier.model_version}",
                "ocr": f"{self.ocr.model_name}@{self.ocr.model_version}",
                "kie": f"{self.kie.model_name}@{self.kie.model_version}",
            },
            trace_id=str(uuid4()),
            warnings=warnings,
        )
