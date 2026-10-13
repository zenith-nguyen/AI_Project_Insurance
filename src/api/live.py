"""Live orchestration for golden claims and locally registered model artifacts."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

import numpy as np
import pandas as pd
from src.data.common import sha256
from src.document.schema import ExtractedField
from src.document.runtime import DocumentRuntimeAdapter
from src.features.preprocessing import features
from src.graph.claim_graph import build_graph, claim_features
from src.integration.consistency import check_amount, check_document_date, check_plate
from src.image.inference import YOLODamageAdapter
from src.media_authenticity import MediaAuthenticityAnalyzer
from src.registry import ModelRegistry

from .schemas import AnalyzeRequest, CaptureSessionRecord, ClaimAnalysis, ClaimIntakeRecord, ClaimIntakeRequest, CorrectionRecord, CorrectionRequest, Evidence, EvidenceUploadRecord, MediaAuthenticityReport, ReviewRecord, ReviewRequest, Signal
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
            "graph": json.loads((claim_root / "entities.json").read_text(encoding="utf-8")) if (claim_root / "entities.json").is_file() else {
                "data_status": "not_provided", "scored_at": json.loads(claim_file.read_text(encoding="utf-8")).get("scored_at"),
                "known_risky_claims": [], "nodes": [], "edges": [],
            },
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
        self.damage = None
        yolo_weights = os.getenv("INSURANCE_YOLO_WEIGHTS")
        if yolo_weights:
            registered_damage = registry.modules["damage_segmentation"]
            self.damage = YOLODamageAdapter(
                yolo_weights,
                expected_sha256=registered_damage.artifact_hash,
                device=os.getenv("INSURANCE_YOLO_DEVICE"),
            )
        self.document_runtime = None
        layout_checkpoint = os.getenv("INSURANCE_LAYOUTLM_CHECKPOINT")
        if layout_checkpoint:
            registered_kie = registry.modules["document_kie"]
            self.document_runtime = DocumentRuntimeAdapter(
                layout_checkpoint,
                expected_tree_hash=registered_kie.artifact_hash,
                device=os.getenv("INSURANCE_DOCUMENT_DEVICE"),
            )
        self.store = JsonlAuditStore(audit_log)
        self.analyses: dict[str, ClaimAnalysis] = {}

    def intake(self, claim_id: str, request: ClaimIntakeRequest) -> ClaimIntakeRecord:
        return self.runtime_store.create(claim_id, request)

    def start_capture(self, claim_id: str) -> CaptureSessionRecord:
        return self.runtime_store.create_capture_session(claim_id)

    def upload(
        self, claim_id: str, kind: str, filename: str, content_type: str | None, content: bytes,
        capture_session_id: str | None = None, challenge_step: int | None = None,
    ) -> EvidenceUploadRecord:
        record = self.runtime_store.save_evidence(
            claim_id, kind, filename, content_type, content, capture_session_id, challenge_step,
        )
        if kind == "image":
            try:
                report = self.authenticity(claim_id, record.evidence_id)
                return record.model_copy(update={"authenticity_verdict": report.verdict})
            except Exception:
                return record.model_copy(update={"authenticity_verdict": "error"})
        return record

    def authenticity(self, claim_id: str, evidence_id: str) -> MediaAuthenticityReport:
        matches = self.runtime_store.find_image_reuse(claim_id, evidence_id)
        cached = self.runtime_store.load_authenticity(claim_id, evidence_id)
        cached_matches = (cached or {}).get("image_info", {}).get("cross_claim_matches", [])
        if cached is not None and cached.get("analyzer_version") == MediaAuthenticityAnalyzer.version and cached_matches == matches:
            return MediaAuthenticityReport.model_validate(cached)
        path = self.runtime_store.evidence_path(claim_id, evidence_id)
        report = self.media_authenticity.analyze(path, evidence_id=evidence_id, reuse_matches=matches)
        self.runtime_store.save_authenticity(claim_id, evidence_id, report.model_dump())
        return report

    def readiness(self) -> dict:
        modules = {
            "tabular_risk": {"active": True, "version": "tabular_v1"},
            "consistency": {"active": True, "version": "consistency_v1"},
            "relationships": {"active": True, "version": "point_in_time_v1"},
            "media_authenticity": {
                "active": True, "version": MediaAuthenticityAnalyzer.version,
                "exiftool": bool(self.media_authenticity.exiftool),
                "c2patool": bool(self.media_authenticity.c2patool),
                "synthid": False,
            },
            "damage_segmentation": {
                "active": self.damage is not None,
                "reason": None if self.damage is not None else "Set INSURANCE_YOLO_WEIGHTS and install requirements-gpu.txt.",
            },
            "document_pipeline": {
                "active": self.document_runtime is not None,
                "reason": None if self.document_runtime is not None else "Set INSURANCE_LAYOUTLM_CHECKPOINT and install document dependencies.",
            },
        }
        return {
            "mode": "live", "fully_live": all(modules[name]["active"] for name in ("damage_segmentation", "document_pipeline")),
            "modules": modules,
        }

    @staticmethod
    def _fields(document: dict) -> list[ExtractedField]:
        return [ExtractedField(**field) for field in document.get("fields", [])]

    def analyze(self, claim_id: str, request: AnalyzeRequest) -> ClaimAnalysis:
        payload = self.repository.load(claim_id)
        claim, documents, graph_payload = payload["claim"], payload["documents"], payload["graph"]
        claim_amount = request.claim_amount if request.claim_amount is not None else claim["claim_amount"]
        incident_date = request.incident_date or claim["incident_date"]
        plate_number = request.plate_number or claim["plate_number"]
        module_status: dict[str, dict[str, object]] = {}
        risk = None
        try:
            risk = self.risk.predict(claim.get("tabular_features", {}))
            module_status["tabular_risk"] = {"status": "completed", "reason": None}
        except (KeyError, TypeError, ValueError) as error:
            module_status["tabular_risk"] = {
                "status": "blocked_missing_input", "reason": str(error),
            }
        signals: list[Signal] = []
        evidence = [Evidence(evidence_id="claim-intake", kind="claim", label="Golden claim intake")]
        extracted: dict[str, object] = {"claim_amount": claim_amount, "incident_date": incident_date, "plate_number": plate_number}
        authenticity_reports: list[dict] = []
        damage_detections: list[dict] = []
        document_results: list[dict] = []
        runtime_warnings: list[str] = []
        image_count = 0
        document_count = len(documents)
        authenticity_failures = 0
        damage_failures = 0
        document_failures = 0
        capture_steps: dict[str, set[int]] = {}

        for item in payload.get("uploaded_evidence", []):
            evidence.append(Evidence(
                evidence_id=item["evidence_id"], kind=item["kind"], label=item["original_filename"],
                source_uri=item["stored_uri"], observed_at=item["observed_at"],
            ))
            if item["kind"] == "document":
                document_count += 1
            if item.get("capture_session_id") and item.get("challenge_step"):
                capture_steps.setdefault(item["capture_session_id"], set()).add(int(item["challenge_step"]))
            if item["kind"] == "image":
                image_count += 1
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
                    authenticity_failures += 1
                    authenticity_reports.append({
                        "evidence_id": item["evidence_id"], "verdict": "error",
                        "error": type(error).__name__,
                    })
                if self.damage is not None:
                    try:
                        image_path = self.runtime_store.evidence_path(claim_id, item["evidence_id"])
                        detections = self.damage.predict(image_path)
                        for detection in detections:
                            detection.update({"evidence_id": item["evidence_id"]})
                        damage_detections.extend(detections)
                        if detections:
                            labels = sorted({detection["class_name"] for detection in detections})
                            signals.append(Signal(
                                signal_id=f"{item['evidence_id']}-damage", category="damage",
                                title="Phát hiện vùng hư hỏng trên ảnh",
                                explanation=f"YOLO phát hiện {len(detections)} vùng: {', '.join(labels)}.",
                                severity="review", evidence_ids=[item["evidence_id"]],
                                confidence=max(detection["confidence"] for detection in detections),
                                model_name=self.damage.model_name, model_version=self.damage.model_version,
                            ))
                    except Exception as error:
                        damage_failures += 1
                        runtime_warnings.append(f"Damage inference failed for {item['evidence_id']}: {type(error).__name__}.")
            elif item["kind"] == "document" and self.document_runtime is not None:
                try:
                    document_path = self.runtime_store.evidence_path(claim_id, item["evidence_id"])
                    result = self.document_runtime.process(document_path, claim_id, item["evidence_id"])
                    document_results.append(result.to_dict())
                    extracted.update({field.field_name: field.normalized_value for field in result.fields})
                    checks = [
                        check_amount(claim_id, claim_amount, result.fields, result.document_id),
                        check_document_date(claim_id, incident_date, result.fields, result.document_id),
                        check_plate(claim_id, plate_number, result.fields, result.document_id),
                    ]
                    signals.append(Signal(
                        signal_id=f"{item['evidence_id']}-document", category="document",
                        title=f"Chứng từ được nhận dạng: {result.document_type}",
                        explanation=f"Đã đọc {len(result.tokens)} vùng chữ và trích xuất {len(result.fields)} trường.",
                        severity="info", evidence_ids=[item["evidence_id"]],
                        confidence=result.document_type_confidence,
                        model_name="dit-paddleocr-layoutlmv3", model_version="document_live_v1",
                    ))
                    for check in checks:
                        if check.status == "fail":
                            signals.append(Signal(
                                signal_id=f"{item['evidence_id']}-{check.reason_code}", category="consistency",
                                title="Thông tin chứng từ cần đối chiếu",
                                explanation=f"Kiểm tra {check.check_name}: {check.reason_code}.",
                                severity="review", evidence_ids=[item["evidence_id"]],
                                model_name="python_rules", model_version="consistency_v1",
                            ))
                except Exception as error:
                    document_failures += 1
                    runtime_warnings.append(f"Document inference failed for {item['evidence_id']}: {type(error).__name__}.")

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

        graph_available = graph_payload.get("data_status", "provided") == "provided"
        if graph_available:
            graph = build_graph(graph_payload["nodes"], graph_payload["edges"], graph_payload["scored_at"])
            graph_values = claim_features(graph, claim_id, set(graph_payload.get("known_risky_claims", [])))
            graph_values["data_status"] = "provided"
            module_status["relationships"] = {"status": "completed", "reason": None}
            evidence.append(Evidence(evidence_id="relationship-graph", kind="relationship", label="Point-in-time relationship graph"))
        else:
            graph_values = {"data_status": "not_provided"}
            module_status["relationships"] = {
                "status": "skipped_missing_input",
                "reason": "No relationship/entity feed was provided for this claim.",
            }
        if graph_available and graph_values["shared_entity_count"]:
            signals.append(Signal(
                signal_id="shared-entity", category="relationship", title="Có thực thể dùng chung",
                explanation=f"Hồ sơ có {graph_values['shared_entity_count']} thực thể liên kết với hồ sơ khác trước thời điểm chấm.",
                severity="review", evidence_ids=["relationship-graph"], model_name="networkx", model_version="point_in_time_v1",
            ))
        if risk is not None and risk["priority"] != "normal":
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
        extracted["damage_detections"] = damage_detections
        extracted["document_results"] = document_results
        extracted["guided_capture"] = {
            "sessions": [
                {"session_id": session_id, "submitted_steps": sorted(steps), "complete": len(steps) == 3}
                for session_id, steps in sorted(capture_steps.items())
            ],
            "assurance": "guided_unverified" if capture_steps else "not_used",
        }
        completeness = (len(required) - len(missing)) / len(required) if required else 1.0
        has_documents = document_count > 0
        document_fields_available = bool(documents or document_results)
        module_status["document_pipeline"] = {
            "status": "completed" if document_fields_available else (
                "error" if document_failures else "unavailable" if has_documents else "skipped_missing_input"
            ),
            "reason": None if document_fields_available else (
                "Document inference failed." if document_failures else
                "Document checkpoint/dependencies are not configured." if has_documents else "No claim document was provided."
            ),
        }
        module_status["damage_segmentation"] = {
            "status": ("error" if damage_failures else "completed" if self.damage is not None else "unavailable") if image_count else "skipped_missing_input",
            "reason": ("Damage inference failed." if damage_failures else None if self.damage is not None else "YOLO checkpoint is not configured.") if image_count else "No vehicle image was provided.",
        }
        module_status["media_authenticity"] = {
            "status": ("error" if authenticity_failures == image_count else "completed") if image_count else "skipped_missing_input",
            "reason": "Authenticity analysis failed." if image_count and authenticity_failures == image_count else None if image_count else "No image was provided.",
        }
        module_status["consistency"] = {
            "status": "completed" if document_fields_available else "skipped_missing_input",
            "reason": None if document_fields_available else "No document fields were available for comparison.",
        }
        module_status["guided_capture"] = {
            "status": "completed" if any(len(steps) == 3 for steps in capture_steps.values()) else (
                "partial" if capture_steps else "skipped_optional"
            ),
            "reason": None if any(len(steps) == 3 for steps in capture_steps.values()) else (
                "A guided capture session has incomplete steps." if capture_steps else "Guided capture was not requested."
            ),
        }
        analysis_status = "blocked" if risk is None else ("partial" if missing or any(
            item["status"] in {"skipped_missing_input", "unavailable", "blocked_missing_input", "error"}
            for item in module_status.values()
        ) else "complete")
        priority = "high" if any(signal.severity == "high" for signal in signals) else ("review" if signals else "normal")
        analysis = ClaimAnalysis(
            claim_id=claim_id, trace_id=uuid4().hex, created_at=datetime.now(timezone.utc).isoformat(), mode="live",
            analysis_status=analysis_status, priority=priority,
            research_risk_score=risk["score"] if risk is not None else None, risk_score_is_probability=False,
            evidence_completeness=completeness, missing_evidence=missing, evidence=evidence, signals=signals,
            extracted_fields=extracted, graph_features=graph_values,
            model_versions={
                "tabular_risk": "tabular_v1", "consistency": "consistency_v1",
                "relationships": "point_in_time_v1", "media_authenticity": MediaAuthenticityAnalyzer.version,
                **({"damage_segmentation": self.damage.model_version} if self.damage is not None else {}),
                **({"document_pipeline": "dit-paddleocr-layoutlmv3-live-v1"} if self.document_runtime is not None else {}),
            },
            module_status=module_status,
            warnings=[
                "Research risk score is not a calibrated production fraud probability.",
                *( ["Analysis is partial: the risk score remains available, but one or more evidence modules could not run."] if analysis_status == "partial" else [] ),
                *( ["Risk scoring is blocked because required tabular model inputs are incomplete."] if analysis_status == "blocked" else [] ),
                *( ["Relationship data was not provided; zero graph risk must not be inferred."] if not graph_available else [] ),
                *( ["Document fields are precomputed inputs; OCR and LayoutLMv3 were not invoked by this request."] if self.document_runtime is None else [] ),
                *( ["YOLO was not invoked because INSURANCE_YOLO_WEIGHTS is not configured."] if self.damage is None else [] ),
                "No authenticity signal is proof that an image is camera-original; provenance may be absent or stripped.",
                *runtime_warnings,
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
