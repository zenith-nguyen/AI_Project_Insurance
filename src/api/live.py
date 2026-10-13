"""Live orchestration for golden claims and locally registered model artifacts."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

import numpy as np
import pandas as pd
from src.data.common import sha256
from src.document.schema import ExtractedField
from src.features.preprocessing import features
from src.graph.claim_graph import build_graph, claim_features
from src.integration.consistency import check_amount, check_document_date, check_plate
from src.registry import ModelRegistry

from .schemas import AnalyzeRequest, ClaimAnalysis, CorrectionRecord, CorrectionRequest, Evidence, ReviewRecord, ReviewRequest, Signal


class GoldenClaimRepository:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def load(self, claim_id: str) -> dict:
        claim_root = self.root / claim_id
        claim_file = claim_root / "claim.json"
        if not claim_file.is_file():
            raise KeyError(claim_id)
        documents = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((claim_root / "documents").glob("*.json"))]
        return {
            "claim": json.loads(claim_file.read_text(encoding="utf-8")),
            "documents": documents,
            "images": json.loads((claim_root / "vehicle_images/manifest.json").read_text(encoding="utf-8")),
            "graph": json.loads((claim_root / "entities.json").read_text(encoding="utf-8")),
        }


class TabularRiskAdapter:
    def __init__(self, artifact: str | Path) -> None:
        import joblib

        self.artifact = Path(artifact)
        if not self.artifact.is_file():
            raise FileNotFoundError(self.artifact)
        self.bundle = joblib.load(self.artifact)

    def predict(self, values: dict) -> dict:
        frame = pd.DataFrame([values])
        # tabular_v1 predates the bias-aware candidate and expects insured_hobbies.
        x = features(frame, exclude_biased_features=False)
        expected = self.bundle["feature_columns"]
        missing = sorted(set(expected) - set(x.columns))
        if missing:
            raise ValueError(f"Golden claim is missing model features: {missing}")
        raw = np.clip(self.bundle["model"].predict_proba(x[expected])[:, 1], 1e-6, 1 - 1e-6)
        score = float(self.bundle["calibrator"].predict_proba(np.log(raw / (1 - raw)).reshape(-1, 1))[0, 1])
        thresholds = self.bundle["thresholds"]
        queue = "high" if score >= thresholds["t2"] else ("review" if score >= thresholds["t1"] else "normal")
        return {"score": score, "priority": queue}


class JsonlAuditStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = Lock()

    def append(self, event_type: str, record: ReviewRecord | CorrectionRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"event_type": event_type, **record.model_dump()}
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


class LiveClaimService:
    def __init__(self, root: Path, registry: ModelRegistry, audit_log: str | Path) -> None:
        self.root = root
        self.registry = registry
        self.repository = GoldenClaimRepository(root / "data/golden/claims")
        risk = registry.modules["tabular_risk"]
        risk_artifact = root / risk.artifact_uri
        if sha256(risk_artifact) != risk.artifact_hash:
            raise RuntimeError("Registered XGBoost artifact hash does not match the local bundle.")
        self.risk = TabularRiskAdapter(risk_artifact)
        self.store = JsonlAuditStore(audit_log)
        self.analyses: dict[str, ClaimAnalysis] = {}

    @staticmethod
    def _fields(document: dict) -> list[ExtractedField]:
        return [ExtractedField(**field) for field in document.get("fields", [])]

    def analyze(self, claim_id: str, request: AnalyzeRequest) -> ClaimAnalysis:
        payload = self.repository.load(claim_id)
        claim, documents, graph_payload = payload["claim"], payload["documents"], payload["graph"]
        claim_amount = request.claim_amount if request.claim_amount is not None else claim["claim_amount"]
        incident_date = request.incident_date or claim["incident_date"]
        plate_number = request.plate_number or claim["plate_number"]
        risk = self.risk.predict(claim["tabular_features"])
        signals: list[Signal] = []
        evidence = [Evidence(evidence_id="claim-intake", kind="claim", label="Golden claim intake")]
        extracted: dict[str, object] = {"claim_amount": claim_amount, "incident_date": incident_date, "plate_number": plate_number}

        for document in documents:
            document_id = document["document_id"]
            evidence_id = document.get("evidence_id", document_id)
            evidence.append(Evidence(evidence_id=evidence_id, kind="document", label=document["document_type"]))
            fields = self._fields(document)
            checks = [
                check_amount(claim_id, claim_amount, fields, document_id),
                check_document_date(claim_id, incident_date, fields, document_id),
                check_plate(claim_id, plate_number, fields, document_id),
            ]
            extracted.update({field.field_name: field.normalized_value for field in fields})
            for check in checks:
                if check.status == "fail":
                    signals.append(Signal(
                        signal_id=f"{document_id}-{check.reason_code}", category="consistency",
                        title="Thông tin chứng từ cần đối chiếu", explanation=f"Kiểm tra {check.check_name}: {check.reason_code}.",
                        severity="review", evidence_ids=[evidence_id], model_name="python_rules", model_version="consistency_v1",
                    ))

        graph = build_graph(graph_payload["nodes"], graph_payload["edges"], graph_payload["scored_at"])
        graph_values = claim_features(graph, claim_id, set(graph_payload.get("known_risky_claims", [])))
        evidence.append(Evidence(evidence_id="relationship-graph", kind="relationship", label="Point-in-time relationship graph"))
        if graph_values["shared_entity_count"]:
            signals.append(Signal(
                signal_id="shared-entity", category="relationship", title="Có thực thể dùng chung",
                explanation=f"Hồ sơ có {graph_values['shared_entity_count']} thực thể liên kết với hồ sơ khác trước thời điểm chấm.",
                severity="review", evidence_ids=["relationship-graph"], model_name="networkx", model_version="point_in_time_v1",
            ))
        if risk["priority"] != "normal":
            signals.append(Signal(
                signal_id="tabular-priority", category="risk", title="Ưu tiên rà soát theo dữ liệu bảng",
                explanation="Điểm xếp hạng nghiên cứu vượt ngưỡng hàng chờ đã khóa.", severity=risk["priority"],
                evidence_ids=["claim-intake"], confidence=risk["score"], model_name="xgboost", model_version="tabular_v1",
            ))

        required = set(claim.get("required_evidence", []))
        present = {item.evidence_id for item in evidence}
        present |= {
            item["evidence_id"]
            for item in payload["images"].get("images", [])
            if item.get("status") == "available"
        }
        missing = sorted(required - present)
        completeness = (len(required) - len(missing)) / len(required) if required else 1.0
        priority = "high" if any(signal.severity == "high" for signal in signals) else ("review" if signals else "normal")
        analysis = ClaimAnalysis(
            claim_id=claim_id, trace_id=uuid4().hex, created_at=datetime.now(timezone.utc).isoformat(), mode="live",
            priority=priority, research_risk_score=risk["score"], risk_score_is_probability=False,
            evidence_completeness=completeness, missing_evidence=missing, evidence=evidence, signals=signals,
            extracted_fields=extracted, graph_features=graph_values,
            model_versions={"tabular_risk": "tabular_v1", "consistency": "consistency_v1", "relationships": "point_in_time_v1"},
            warnings=[
                "Research risk score is not a calibrated production fraud probability.",
                "Document fields are golden precomputed inputs; OCR and LayoutLMv3 were not invoked by this request.",
                "Vehicle image binary is absent; YOLO was not invoked by this request.",
                "Human review is required.",
            ],
        )
        self.analyses[claim_id] = analysis
        return analysis

    def get_analysis(self, claim_id: str) -> ClaimAnalysis | None:
        return self.analyses.get(claim_id)

    def review(self, claim_id: str, request: ReviewRequest) -> ReviewRecord:
        analysis = self.get_analysis(claim_id)
        if analysis is None:
            raise KeyError(claim_id)
        record = ReviewRecord(claim_id=claim_id, trace_id=analysis.trace_id, **request.model_dump())
        self.store.append("review", record)
        return record

    def correct(self, claim_id: str, request: CorrectionRequest) -> CorrectionRecord:
        analysis = self.get_analysis(claim_id)
        if analysis is None:
            raise KeyError(claim_id)
        record = CorrectionRecord(claim_id=claim_id, trace_id=analysis.trace_id, **request.model_dump())
        self.store.append("field_correction", record)
        return record
