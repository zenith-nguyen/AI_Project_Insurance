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
from src.media_authenticity import MediaAuthenticityAnalyzer
from src.registry import ModelRegistry

from .schemas import AnalyzeRequest, ClaimAnalysis, ClaimIntakeRecord, ClaimIntakeRequest, CorrectionRecord, CorrectionRequest, Evidence, EvidenceUploadRecord, MediaAuthenticityReport, ReviewRecord, ReviewRequest, Signal
from .storage import RuntimeClaimStore


class ClaimRepository:
    def __init__(self, golden_root: str | Path, runtime_root: str | Path) -> None:
        self.golden_root = Path(golden_root)
        self.runtime_root = Path(runtime_root)

    def load(self, claim_id: str) -> dict:
        candidates = [self.runtime_root / claim_id, self.golden_root / claim_id]
        claim_root = next((path for path in candidates if (path / "claim.json").is_file()), candidates[-1])
        claim_file = claim_root / "claim.json"
        if not claim_file.is_file():
            raise KeyError(claim_id)
        documents = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((claim_root / "documents").glob("*.json"))]
        image_manifest = claim_root / "vehicle_images/manifest.json"
        evidence_manifest = claim_root / "evidence_manifest.json"
        return {
            "claim": json.loads(claim_file.read_text(encoding="utf-8")),
            "documents": documents,
            "images": json.loads(image_manifest.read_text(encoding="utf-8")) if image_manifest.is_file() else {"images": []},
            "uploaded_evidence": json.loads(evidence_manifest.read_text(encoding="utf-8")) if evidence_manifest.is_file() else [],
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
    def __init__(self, root: Path, registry: ModelRegistry, audit_log: str | Path, runtime_claim_root: str | Path | None = None) -> None:
        self.root = root
        self.registry = registry
        runtime_claims = Path(runtime_claim_root) if runtime_claim_root else root / "runtime/claims"
        self.repository = ClaimRepository(root / "data/golden/claims", runtime_claims)
        self.runtime_store = RuntimeClaimStore(runtime_claims)
        risk = registry.modules["tabular_risk"]
        risk_artifact = root / risk.artifact_uri
        if sha256(risk_artifact) != risk.artifact_hash:
            raise RuntimeError("Registered XGBoost artifact hash does not match the local bundle.")
        self.risk = TabularRiskAdapter(risk_artifact)
        self.media_authenticity = MediaAuthenticityAnalyzer()
        self.store = JsonlAuditStore(audit_log)
        self.analyses: dict[str, ClaimAnalysis] = {}

    def intake(self, claim_id: str, request: ClaimIntakeRequest) -> ClaimIntakeRecord:
        return self.runtime_store.create(claim_id, request)

    def upload(self, claim_id: str, kind: str, filename: str, content_type: str | None, content: bytes) -> EvidenceUploadRecord:
        return self.runtime_store.save_evidence(claim_id, kind, filename, content_type, content)

    def authenticity(self, claim_id: str, evidence_id: str) -> MediaAuthenticityReport:
        path = self.runtime_store.evidence_path(claim_id, evidence_id)
        return self.media_authenticity.analyze(path, evidence_id=evidence_id)

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
        authenticity_reports: list[dict] = []

        for item in payload.get("uploaded_evidence", []):
            evidence.append(Evidence(
                evidence_id=item["evidence_id"], kind=item["kind"], label=item["original_filename"],
                source_uri=item["stored_uri"], observed_at=item["observed_at"],
            ))
            if item["kind"] == "image":
                try:
                    report = self.authenticity(claim_id, item["evidence_id"])
                    authenticity_reports.append(report.model_dump())
                    flagged = [finding for finding in report.findings if finding.outcome == "detected" and finding.severity in {"review", "high"}]
                    if flagged:
                        severity = "high" if any(finding.severity == "high" for finding in flagged) else "review"
                        signals.append(Signal(
                            signal_id=f"{item['evidence_id']}-authenticity", category="authenticity",
                            title="Nguồn gốc ảnh cần được kiểm tra",
                            explanation=" ".join(finding.explanation for finding in flagged),
                            severity=severity, evidence_ids=[item["evidence_id"]],
                            confidence=max((finding.confidence or 0.0) for finding in flagged),
                            model_name="media_authenticity", model_version=MediaAuthenticityAnalyzer.version,
                        ))
                except Exception as error:
                    authenticity_reports.append({
                        "evidence_id": item["evidence_id"], "verdict": "error",
                        "error": type(error).__name__,
                    })

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
        if any(item.kind == "image" for item in evidence):
            present.add("vehicle_image")
        if any(item.kind == "document" for item in evidence):
            present.add("claim_document")
        missing = sorted(required - present)
        extracted["media_authenticity"] = authenticity_reports
        completeness = (len(required) - len(missing)) / len(required) if required else 1.0
        priority = "high" if any(signal.severity == "high" for signal in signals) else ("review" if signals else "normal")
        analysis = ClaimAnalysis(
            claim_id=claim_id, trace_id=uuid4().hex, created_at=datetime.now(timezone.utc).isoformat(), mode="live",
            priority=priority, research_risk_score=risk["score"], risk_score_is_probability=False,
            evidence_completeness=completeness, missing_evidence=missing, evidence=evidence, signals=signals,
            extracted_fields=extracted, graph_features=graph_values,
            model_versions={"tabular_risk": "tabular_v1", "consistency": "consistency_v1", "relationships": "point_in_time_v1", "media_authenticity": MediaAuthenticityAnalyzer.version},
            warnings=[
                "Research risk score is not a calibrated production fraud probability.",
                "Document fields are golden precomputed inputs; OCR and LayoutLMv3 were not invoked by this request.",
                "Vehicle image binary is absent; YOLO was not invoked by this request.",
                "No authenticity signal is proof that an image is camera-original; provenance may be absent or stripped.",
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
