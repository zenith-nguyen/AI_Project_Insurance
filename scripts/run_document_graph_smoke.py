"""Run a dependency-light smoke test of the document-to-review contract."""
from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.document.classifier import Classification
from src.document.kie import RuleBasedKIE
from src.document.pipeline import DocumentPipeline
from src.document.schema import OCRToken
from src.graph.claim_graph import build_graph, claim_features
from src.integration.consistency import check_amount, check_document_date, check_plate
from src.integration.review import ClaimReviewResult


class DemoClassifier:
    model_name = "demo-classifier"
    model_version = "v1"

    def predict(self, images):
        return [Classification("invoice", 0.91, {"invoice": 0.91}) for _ in images]


class DemoOCR:
    model_name = "demo-ocr"
    model_version = "v1"

    def predict(self, image):
        return [
            OCRToken(
                "Invoice No: INV-001 Date 11/10/2026 Total: 10,200,000 VND Plate 51A-12345",
                0.93,
            )
        ]


def main() -> None:
    claim_id, document_id = "CLM-DEMO-001", "DOC-DEMO-001"
    document = DocumentPipeline(DemoClassifier(), DemoOCR(), RuleBasedKIE()).process(
        Path("demo-invoice.png"), claim_id, document_id
    )
    checks = [
        check_amount(claim_id, 10_000_000, document.fields, document_id),
        check_document_date(claim_id, "2026-10-01", document.fields, document_id),
        check_plate(claim_id, "51A-12345", document.fields, document_id),
    ]
    graph = build_graph(
        [
            {"id": claim_id, "entity_type": "claim", "available_at": "2026-10-01T00:00:00Z"},
            {"id": "CLM-DEMO-002", "entity_type": "claim", "available_at": "2026-10-02T00:00:00Z"},
            {"id": "PHONE-DEMO", "entity_type": "phone", "available_at": "2026-09-01T00:00:00Z"},
        ],
        [
            {"source": claim_id, "target": "PHONE-DEMO", "relation": "uses", "event_time": "2026-10-01T01:00:00Z"},
            {"source": "CLM-DEMO-002", "target": "PHONE-DEMO", "relation": "uses", "event_time": "2026-10-02T01:00:00Z"},
        ],
        "2026-10-11T00:00:00Z",
    )
    review = ClaimReviewResult(
        claim_id,
        documents=[document.to_dict()],
        consistency_checks=checks,
        graph_features=claim_features(graph, claim_id),
        model_versions=document.model_versions,
    )
    print(json.dumps(review.to_dict(), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
