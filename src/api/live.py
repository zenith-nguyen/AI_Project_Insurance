"""Live orchestration for golden claims and locally registered model artifacts."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from collections.abc import Callable
from uuid import uuid4

import numpy as np
import pandas as pd
from src.data.common import sha256
from src.document.schema import DocumentResult, ExtractedField
from src.document.runtime import DocumentRuntimeAdapter
from src.features.preprocessing import features
from src.graph.claim_graph import build_graph, claim_features, normalize_entity
from src.integration.consistency import check_amount, check_document_date, check_plate
from src.image.inference import YOLODamageAdapter
from src.image.plate import VehiclePlateReader, normalize_plate
from src.media_authenticity import CalibratedImageForensics, MediaAuthenticityAnalyzer
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
        claim = json.loads(claim_file.read_text(encoding="utf-8"))
        graph_path = claim_root / "entities.json"
        graph = json.loads(graph_path.read_text(encoding="utf-8")) if graph_path.is_file() else None
        if claim_root.parent == self.runtime_root and (not graph or graph.get("data_status") == "not_provided"):
            graph = self._runtime_relationship_graph(claim_id, claim)
        return {
            "claim": claim,
            "documents": documents,
            "images": json.loads(image_manifest.read_text(encoding="utf-8")) if image_manifest.is_file() else {"images": []},
            "uploaded_evidence": json.loads(evidence_manifest.read_text(encoding="utf-8")) if evidence_manifest.is_file() else [],
            "graph": graph or {"data_status": "not_provided", "scored_at": claim.get("scored_at"), "known_risky_claims": [], "nodes": [], "edges": []},
        }

    @staticmethod
    def _relationship_values(claim: dict) -> dict[str, str]:
        values = {
            key: value for key, value in claim.get("relationship_entities", {}).items()
            if value and key != "relationship_scope"
        }
        if claim.get("plate_number"):
            values.setdefault("vehicle_plate", claim["plate_number"])
        return {key: normalize_entity(key, value) for key, value in values.items() if value}

    def _runtime_relationship_graph(self, claim_id: str, claim: dict) -> dict:
        target_values = self._relationship_values(claim)
        target_scope = claim.get("relationship_entities", {}).get("relationship_scope")
        scored_at = claim.get("scored_at") or claim.get("created_at")
        if not target_values:
            return {"data_status": "not_provided", "scored_at": scored_at, "known_risky_claims": [], "nodes": [], "edges": []}
        target_keys = {(kind, value) for kind, value in target_values.items()}
        nodes: dict[str, dict] = {}
        edges: list[dict] = []
        for candidate_file in sorted(self.runtime_root.glob("*/claim.json")):
            candidate = json.loads(candidate_file.read_text(encoding="utf-8"))
            if target_scope and candidate.get("relationship_entities", {}).get("relationship_scope") != target_scope:
                continue
            # scored_at is the point-in-time business timestamp. created_at is
            # only the ingestion timestamp and may be later when importing an
            # approved historical record for graph evaluation.
            available_at = candidate.get("scored_at") or candidate.get("created_at")
            if not available_at or datetime.fromisoformat(available_at.replace("Z", "+00:00")) > datetime.fromisoformat(scored_at.replace("Z", "+00:00")):
                continue
            candidate_id = candidate.get("claim_id")
            shared = set(self._relationship_values(candidate).items()) & target_keys
            if candidate_id == claim_id:
                shared = target_keys
            if not shared:
                continue
            nodes[candidate_id] = {"id": candidate_id, "entity_type": "claim", "available_at": available_at}
            for kind, value in sorted(shared):
                digest = hashlib.sha256(f"{kind}:{value}".encode()).hexdigest()[:16]
                entity_id = f"entity:{kind}:{digest}"
                nodes[entity_id] = {"id": entity_id, "entity_type": kind, "available_at": available_at}
                edges.append({"source": candidate_id, "target": entity_id, "event_time": available_at, "relation": "reported_entity"})
        return {"data_status": "provided", "scored_at": scored_at, "known_risky_claims": [], "nodes": list(nodes.values()), "edges": edges}


class TabularRiskAdapter:
    def __init__(self, artifact: str | Path) -> None:
        import joblib

        self.artifact = Path(artifact)
        if not self.artifact.is_file():
            raise FileNotFoundError(self.artifact)
        self.bundle = joblib.load(self.artifact)

    @staticmethod
    def _business_group(feature: str) -> str:
        if feature.startswith("policy_") or feature in {"umbrella_limit", "months_as_customer"}:
            return "policy"
        if feature.startswith("insured_") or feature in {"age", "capital_gains", "capital_loss"}:
            return "customer"
        if feature.startswith("incident_") or feature in {
            "collision_type", "authorities_contacted", "number_of_vehicles_involved",
            "property_damage", "bodily_injuries", "witnesses", "police_report_available",
        }:
            return "incident"
        if feature in {"total_claim_amount", "injury_claim", "property_claim", "vehicle_claim"}:
            return "claim_cost"
        if feature.startswith("auto_"):
            return "vehicle"
        return "other"

    def prepare(self, values: dict) -> tuple[pd.DataFrame, dict]:
        frame = pd.DataFrame([values])
        # tabular_v1 predates the bias-aware candidate and expects insured_hobbies.
        x = features(frame, exclude_biased_features=False)
        expected = list(self.bundle["feature_columns"])
        missing = sorted(set(expected) - set(x.columns))
        groups = sorted({self._business_group(feature) for feature in missing})
        summary = {
            "required_field_count": len(expected),
            "provided_field_count": len(expected) - len(missing),
            "missing_field_count": len(missing),
            "missing_fields": missing,
            "missing_business_groups": groups,
        }
        return x, summary

    def predict(self, values: dict) -> dict:
        x, input_summary = self.prepare(values)
        expected = list(self.bundle["feature_columns"])
        missing = input_summary["missing_fields"]
        if missing:
            raise ValueError(f"Golden claim is missing model features: {missing}")
        raw = np.clip(self.bundle["model"].predict_proba(x[expected])[:, 1], 1e-6, 1 - 1e-6)
        score = float(self.bundle["calibrator"].predict_proba(np.log(raw / (1 - raw)).reshape(-1, 1))[0, 1])
        thresholds = self.bundle["thresholds"]
        queue = "high" if score >= thresholds["t2"] else ("review" if score >= thresholds["t1"] else "normal")
        return {"score": score, "priority": queue, "input_summary": input_summary}


class JsonlAuditStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = Lock()

    def append(self, event_type: str, record: ReviewRecord | CorrectionRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"event_type": event_type, **record.model_dump()}
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")

    def list_claim(self, claim_id: str, limit: int = 100) -> list[dict]:
        if not self.path.is_file():
            return []
        with self._lock, self.path.open("r", encoding="utf-8") as stream:
            rows = [json.loads(line) for line in stream if line.strip()]
        return [row for row in rows if row.get("claim_id") == claim_id][-limit:]

    def list_all(self, limit: int = 5000) -> list[dict]:
        if not self.path.is_file():
            return []
        with self._lock, self.path.open("r", encoding="utf-8") as stream:
            rows = [json.loads(line) for line in stream if line.strip()]
        return rows[-limit:]


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
        forensic_runner = None
        forensic_checkpoint = os.getenv("INSURANCE_FORENSIC_CHECKPOINT")
        forensic_calibration = os.getenv("INSURANCE_FORENSIC_CALIBRATION")
        if forensic_checkpoint or forensic_calibration:
            if not forensic_checkpoint or not forensic_calibration:
                raise RuntimeError("Set both INSURANCE_FORENSIC_CHECKPOINT and INSURANCE_FORENSIC_CALIBRATION.")
            forensic_runner = CalibratedImageForensics(
                forensic_checkpoint, forensic_calibration, device=os.getenv("INSURANCE_FORENSIC_DEVICE"),
            )
        self.media_authenticity = MediaAuthenticityAnalyzer(forensic_runner=forensic_runner)
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
        self.plate_reader = None
        layout_checkpoint = os.getenv("INSURANCE_LAYOUTLM_CHECKPOINT")
        if layout_checkpoint:
            registered_kie = registry.modules["document_kie"]
            self.document_runtime = DocumentRuntimeAdapter(
                layout_checkpoint,
                expected_tree_hash=registered_kie.artifact_hash,
                device=os.getenv("INSURANCE_DOCUMENT_DEVICE"),
            )
            if os.getenv("INSURANCE_ENABLE_VEHICLE_PLATE_OCR", "1").lower() in {"1", "true", "yes"}:
                self.plate_reader = VehiclePlateReader(self.document_runtime.read_image_text)
            if os.getenv("INSURANCE_PRELOAD_MODELS", "0").lower() in {"1", "true", "yes"}:
                self.document_runtime.start_warmup()
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
        self.analyses.pop(claim_id, None)
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
            "tabular_risk": {"active": True, "version": self.registry.modules["tabular_risk"].version},
            "consistency": {"active": True, "version": self.registry.modules["consistency"].version},
            "relationships": {"active": True, "version": self.registry.modules["relationships"].version},
            "media_authenticity": {
                "active": True, "version": MediaAuthenticityAnalyzer.version,
                "exiftool": bool(self.media_authenticity.exiftool),
                "c2patool": bool(self.media_authenticity.c2patool),
                "synthid": False,
                "pixel_forensics": bool(self.media_authenticity.forensic_runner),
            },
            "damage_segmentation": {
                "active": self.damage is not None,
                "reason": None if self.damage is not None else "Set INSURANCE_YOLO_WEIGHTS and install requirements-gpu.txt.",
            },
            "vehicle_plate_reader": {
                "active": self.plate_reader is not None,
                "reason": None if self.plate_reader is not None else "Document OCR is required for local vehicle-plate reading.",
                "version": self.plate_reader.model_version if self.plate_reader is not None else None,
            },
            "document_pipeline": {
                "active": self.document_runtime is not None,
                "reason": None if self.document_runtime is not None else "Set INSURANCE_LAYOUTLM_CHECKPOINT and install document dependencies.",
                "warmup": self.document_runtime.readiness() if self.document_runtime is not None else None,
                "cache_version": self.document_runtime.cache_version if self.document_runtime is not None else None,
            },
        }
        return {
            "mode": "live", "fully_live": all(modules[name]["active"] for name in ("damage_segmentation", "document_pipeline")),
            "modules": modules,
        }

    @staticmethod
    def _fields(document: dict) -> list[ExtractedField]:
        return [ExtractedField(**field) for field in document.get("fields", [])]

    def analyze(
        self, claim_id: str, request: AnalyzeRequest,
        progress: Callable[[str, str | None], None] | None = None,
    ) -> ClaimAnalysis:
        if progress:
            progress("preparing", None)
        if not request.force_recompute and not any([
            request.claim_amount is not None, request.incident_date, request.plate_number, request.evidence_ids,
        ]):
            cached = self.get_analysis(claim_id)
            if cached is not None:
                if progress:
                    progress("finalizing", "Đang dùng lại kết quả vì hồ sơ và bằng chứng không đổi.")
                return cached
        payload = self.repository.load(claim_id)
        claim, documents, graph_payload = payload["claim"], payload["documents"], payload["graph"]
        claim_amount = request.claim_amount if request.claim_amount is not None else claim["claim_amount"]
        incident_date = request.incident_date or claim["incident_date"]
        plate_number = request.plate_number or claim["plate_number"]
        module_status: dict[str, dict[str, object]] = {}
        if progress:
            progress("tabular", None)
        risk = None
        tabular_values = claim.get("tabular_features", {})
        try:
            _, tabular_input_summary = self.risk.prepare(tabular_values)
        except (KeyError, TypeError, ValueError):
            tabular_input_summary = {
                "required_field_count": 0, "provided_field_count": 0,
                "missing_field_count": 0, "missing_fields": [],
                "missing_business_groups": ["other"],
            }
        try:
            risk = self.risk.predict(tabular_values)
            module_status["tabular_risk"] = {
                "status": "completed", "reason": None, **risk["input_summary"],
            }
        except (KeyError, TypeError, ValueError) as error:
            module_status["tabular_risk"] = {
                "status": "blocked_missing_input", "reason": str(error), **tabular_input_summary,
            }
        signals: list[Signal] = []
        evidence = [Evidence(evidence_id="claim-intake", kind="claim", label="Golden claim intake")]
        extracted: dict[str, object] = {"claim_amount": claim_amount, "incident_date": incident_date, "plate_number": plate_number}
        authenticity_reports: list[dict] = []
        damage_detections: list[dict] = []
        vehicle_plate_readings: list[dict] = []
        document_results: list[dict] = []
        runtime_warnings: list[str] = []
        image_count = 0
        document_count = len(documents)
        authenticity_failures = 0
        damage_failures = 0
        plate_failures = 0
        document_failures = 0
        damage_cache_hits = 0
        plate_cache_hits = 0
        document_cache_hits = 0
        capture_steps: dict[str, set[int]] = {}

        uploaded_evidence = payload.get("uploaded_evidence", [])
        image_total = sum(item["kind"] == "image" for item in uploaded_evidence)
        uploaded_document_total = sum(item["kind"] == "document" for item in uploaded_evidence)
        image_index = 0
        document_index = 0
        if progress:
            progress("evidence", None)

        for item in uploaded_evidence:
            evidence.append(Evidence(
                evidence_id=item["evidence_id"], kind=item["kind"], label=item["original_filename"],
                source_uri=item["stored_uri"], observed_at=item["observed_at"],
                content_type=item.get("content_type"), size_bytes=item.get("size_bytes"),
                sha256=item.get("sha256"),
            ))
            if item["kind"] == "document":
                document_count += 1
            if item.get("capture_session_id") and item.get("challenge_step"):
                capture_steps.setdefault(item["capture_session_id"], set()).add(int(item["challenge_step"]))
            if item["kind"] == "image":
                image_count += 1
                image_index += 1
                try:
                    if progress:
                        progress(
                            "image_authenticity",
                            f"Ảnh {image_index}/{image_total}: đang kiểm tra nguồn gốc và khả năng dùng lại.",
                        )
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
                        damage_cache_key = hashlib.sha256(
                            (
                                f"{item.get('sha256', '')}:damage-v1:{self.damage.model_name}:"
                                f"{self.damage.model_version}:{self.registry.modules['damage_segmentation'].artifact_hash}"
                            ).encode()
                        ).hexdigest()
                        cached_damage = None if request.force_recompute else self.runtime_store.load_inference_cache(
                            claim_id, item["evidence_id"], "damage", damage_cache_key,
                        )
                        if progress:
                            progress(
                                "damage",
                                (
                                    f"Ảnh {image_index}/{image_total}: dùng lại vùng hư hỏng đã lưu vì tệp và model không đổi."
                                    if cached_damage is not None else
                                    f"Ảnh {image_index}/{image_total}: YOLO đang khoanh vùng hư hỏng."
                                ),
                            )
                        if cached_damage is not None:
                            detections = [dict(row) for row in cached_damage.get("detections", [])]
                            damage_cache_hits += 1
                        else:
                            image_path = self.runtime_store.evidence_path(claim_id, item["evidence_id"])
                            detections = self.damage.predict(image_path)
                            self.runtime_store.save_inference_cache(
                                claim_id, item["evidence_id"], "damage", damage_cache_key,
                                {"detections": detections},
                            )
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
                if self.plate_reader is not None:
                    try:
                        plate_cache_key = hashlib.sha256(
                            (
                                f"{item.get('sha256', '')}:vehicle-plate-v1:"
                                f"{self.plate_reader.model_version}:{self.document_runtime.cache_version}"
                            ).encode()
                        ).hexdigest()
                        cached_plate = None if request.force_recompute else self.runtime_store.load_inference_cache(
                            claim_id, item["evidence_id"], "vehicle_plate", plate_cache_key,
                        )
                        if progress:
                            progress(
                                "vehicle_plate",
                                (
                                    f"Ảnh {image_index}/{image_total}: dùng lại kết quả đọc biển số đã lưu."
                                    if cached_plate is not None else
                                    f"Ảnh {image_index}/{image_total}: đang tìm và đọc biển số nhìn thấy được."
                                ),
                            )
                        if cached_plate is not None:
                            readings = [dict(row) for row in cached_plate.get("readings", [])]
                            plate_cache_hits += 1
                        else:
                            image_path = self.runtime_store.evidence_path(claim_id, item["evidence_id"])
                            readings = self.plate_reader.predict(image_path)
                            self.runtime_store.save_inference_cache(
                                claim_id, item["evidence_id"], "vehicle_plate", plate_cache_key,
                                {"readings": readings},
                            )
                        for reading in readings:
                            reading.update({"evidence_id": item["evidence_id"]})
                        vehicle_plate_readings.extend(readings)
                        if readings and plate_number and normalize_plate(str(plate_number)) != readings[0]["normalized_value"]:
                            signals.append(Signal(
                                signal_id=f"{item['evidence_id']}-vehicle-plate-mismatch",
                                category="consistency", title="Biển số nhìn thấy trên ảnh khác khai báo",
                                explanation=(
                                    f"OCR đọc biển số {readings[0]['normalized_value']} trên ảnh, "
                                    f"trong khi hồ sơ khai {normalize_plate(str(plate_number))}."
                                ),
                                severity="review", evidence_ids=[item["evidence_id"]],
                                confidence=readings[0]["confidence"], model_name=self.plate_reader.model_name,
                                model_version=self.plate_reader.model_version,
                            ))
                    except Exception as error:
                        plate_failures += 1
                        runtime_warnings.append(f"Vehicle plate reading failed for {item['evidence_id']}: {type(error).__name__}.")
            elif item["kind"] == "document" and self.document_runtime is not None:
                document_index += 1
                try:
                    cache_key_builder = getattr(self.document_runtime, "cache_key", None)
                    document_cache_key = (
                        cache_key_builder(item.get("sha256", ""))
                        if callable(cache_key_builder) else
                        hashlib.sha256(
                            f"{item.get('sha256', '')}:document-v1:{type(self.document_runtime).__name__}".encode()
                        ).hexdigest()
                    )
                    cached_document = None if request.force_recompute else self.runtime_store.load_inference_cache(
                        claim_id, item["evidence_id"], "document", document_cache_key,
                    )
                    if progress:
                        progress(
                            "document_loading",
                            (
                                f"Chứng từ {document_index}/{uploaded_document_total}: dùng lại kết quả OCR/KIE đã lưu vì tệp và model không đổi."
                                if cached_document is not None else
                                f"Chứng từ {document_index}/{uploaded_document_total}: đang chuẩn bị DiT, PaddleOCR và LayoutLMv3."
                            ),
                        )
                    if cached_document is not None:
                        result = DocumentResult.from_dict(cached_document)
                        document_cache_hits += 1
                    else:
                        document_path = self.runtime_store.evidence_path(claim_id, item["evidence_id"])
                        result = self.document_runtime.process(
                            document_path,
                            claim_id,
                            item["evidence_id"],
                            progress=(lambda stage: progress(stage, None)) if progress else None,
                        )
                        self.runtime_store.save_inference_cache(
                            claim_id, item["evidence_id"], "document", document_cache_key, result.to_dict(),
                        )
                    document_results.append(result.to_dict())
                    for warning in result.warnings:
                        runtime_warnings.append(f"{item['evidence_id']}: {warning}")
                        if warning.startswith("kie_model_rule_conflict:"):
                            field_name = warning.split(":", 1)[1]
                            signals.append(Signal(
                                signal_id=f"{item['evidence_id']}-kie-conflict-{field_name}",
                                category="document",
                                title="Trường chứng từ có hai kết quả cần đối chiếu",
                                explanation=(
                                    f"LayoutLMv3 và quy tắc đọc chứng từ không đồng ý ở trường {field_name}. "
                                    "Hệ thống đã áp dụng chính sách confidence đã khóa và lưu nguồn của giá trị được chọn."
                                ),
                                severity="review", evidence_ids=[item["evidence_id"]],
                                model_name="layoutlmv3-rule-hybrid", model_version="v2",
                            ))
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
                                model_name="python_rules", model_version=self.registry.modules["consistency"].version,
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
                        severity="review", evidence_ids=[evidence_id], model_name="python_rules", model_version=self.registry.modules["consistency"].version,
                    ))

        if progress:
            progress("relationships", None)
        graph_available = graph_payload.get("data_status", "provided") == "provided"
        if graph_available:
            graph = build_graph(graph_payload["nodes"], graph_payload["edges"], graph_payload["scored_at"])
            graph_values = claim_features(graph, claim_id, set(graph_payload.get("known_risky_claims", [])))
            neighbor_entities = list(graph.neighbors(claim_id))
            graph_values["shared_entity_types"] = sorted({
                str(graph.nodes[entity].get("entity_type", "unknown"))
                for entity in neighbor_entities if graph.degree(entity) > 1
            })
            graph_values["related_claim_ids"] = sorted({
                str(node)
                for entity in neighbor_entities
                for node in graph.neighbors(entity)
                if node != claim_id and graph.nodes[node].get("entity_type") == "claim"
            })
            relationship_values = self.repository._relationship_values(claim)
            graph_values["query_entity_display"] = {
                kind: (f"••••{value[-4:]}" if kind == "contact_phone" else value.upper() if kind == "vehicle_plate" else value)
                for kind, value in relationship_values.items()
            }
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
                severity="review", evidence_ids=["relationship-graph"], model_name="networkx", model_version=self.registry.modules["relationships"].version,
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
        extracted["vehicle_plate_readings"] = vehicle_plate_readings
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
            "status": "completed" if document_results else "completed_precomputed" if documents else (
                "error" if document_failures else "unavailable" if has_documents else "skipped_missing_input"
            ),
            "reason": "Document fields were prepared for the demo; uploaded file was not read by OCR/KIE." if documents and not document_results else None if document_results else (
                "Document inference failed." if document_failures else
                "Document checkpoint/dependencies are not configured." if has_documents else "No claim document was provided."
            ),
            "evidence_cache_hits": document_cache_hits,
            "evidence_processed": uploaded_document_total,
        }
        module_status["damage_segmentation"] = {
            "status": ("error" if damage_failures else "completed" if self.damage is not None else "unavailable") if image_count else "skipped_missing_input",
            "reason": ("Damage inference failed." if damage_failures else None if self.damage is not None else "YOLO checkpoint is not configured.") if image_count else "No vehicle image was provided.",
            "evidence_cache_hits": damage_cache_hits,
            "evidence_processed": image_total,
        }
        module_status["vehicle_plate_reader"] = {
            "status": ("error" if plate_failures == image_count else "completed") if image_count and self.plate_reader is not None else (
                "unavailable" if image_count else "skipped_missing_input"
            ),
            "reason": (
                "Vehicle plate OCR failed." if image_count and plate_failures == image_count else
                None if image_count and self.plate_reader is not None else
                "Local plate OCR requires the document OCR runtime." if image_count else
                "No vehicle image was provided."
            ),
            "evidence_cache_hits": plate_cache_hits,
            "evidence_processed": image_total,
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
            item["status"] in {"skipped_missing_input", "unavailable", "blocked_missing_input", "error", "completed_precomputed"}
            for item in module_status.values()
        ) else "complete")
        priority = "high" if any(signal.severity == "high" for signal in signals) else ("review" if signals else "normal")
        if progress:
            progress("finalizing", None)
        analysis = ClaimAnalysis(
            claim_id=claim_id, trace_id=uuid4().hex, created_at=datetime.now(timezone.utc).isoformat(), mode="live",
            analysis_status=analysis_status, priority=priority,
            research_risk_score=risk["score"] if risk is not None else None, risk_score_is_probability=False,
            evidence_completeness=completeness, required_evidence_count=len(required),
            present_required_count=max(0, len(required) - len(missing)), missing_evidence=missing,
            evidence=evidence, signals=signals,
            extracted_fields=extracted, graph_features=graph_values,
            model_versions={
                "tabular_risk": self.registry.modules["tabular_risk"].version,
                "consistency": self.registry.modules["consistency"].version,
                "relationships": self.registry.modules["relationships"].version,
                "media_authenticity": MediaAuthenticityAnalyzer.version,
                **({"damage_segmentation": self.damage.model_version} if self.damage is not None else {}),
                **({"document_pipeline": getattr(self.document_runtime, "pipeline_version", "document-runtime-v1")} if self.document_runtime is not None else {}),
                **({"vehicle_plate_reader": self.plate_reader.model_version} if self.plate_reader is not None else {}),
            },
            module_status=module_status,
            warnings=[
                "Research risk score is not a calibrated production fraud probability.",
                *( ["Analysis is partial: the risk score remains available, but one or more evidence modules could not run."] if analysis_status == "partial" else [] ),
                *( ["Risk scoring is blocked because required tabular model inputs are incomplete."] if analysis_status == "blocked" else [] ),
                *( ["Relationship data was not provided; zero graph risk must not be inferred."] if not graph_available else [] ),
                *( ["Document fields are precomputed inputs; OCR and LayoutLMv3 were not invoked for them."] if documents and not document_results else [] ),
                *( ["YOLO was not invoked because INSURANCE_YOLO_WEIGHTS is not configured."] if self.damage is None else [] ),
                "No authenticity signal is proof that an image is camera-original; provenance may be absent or stripped.",
                *runtime_warnings,
                "Human review is required.",
            ],
        )
        self.analyses[claim_id] = analysis
        self.runtime_store.save_analysis(analysis)
        return analysis

    def get_analysis(self, claim_id: str) -> ClaimAnalysis | None:
        cached = self.analyses.get(claim_id)
        if cached is not None:
            return self._enrich_analysis_metadata(claim_id, cached)
        persisted = self.runtime_store.load_analysis(claim_id)
        if persisted is not None:
            persisted = self._enrich_analysis_metadata(claim_id, persisted)
            self.analyses[claim_id] = persisted
        return persisted

    def _enrich_analysis_metadata(self, claim_id: str, analysis: ClaimAnalysis) -> ClaimAnalysis:
        """Backfill explanatory metadata for analyses stored by earlier UI versions."""
        current = dict(analysis.module_status.get("tabular_risk", {}))
        if "missing_field_count" in current:
            return analysis
        try:
            payload = self.repository.load(claim_id)
            _, summary = self.risk.prepare(payload["claim"].get("tabular_features", {}))
        except (KeyError, TypeError, ValueError):
            return analysis
        current.update(summary)
        module_status = {**analysis.module_status, "tabular_risk": current}
        return analysis.model_copy(update={"module_status": module_status})

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

    def events(self, claim_id: str) -> list[dict]:
        self.repository.load(claim_id)
        return self.store.list_claim(claim_id)

    def list_claims(self) -> list[dict]:
        events: dict[str, list[dict]] = {}
        for event in self.store.list_all():
            events.setdefault(str(event.get("claim_id")), []).append(event)
        rows = []
        for claim_file in sorted(self.runtime_store.root.glob("*/claim.json")):
            claim = json.loads(claim_file.read_text(encoding="utf-8-sig"))
            claim_id = str(claim["claim_id"])
            analysis = self.get_analysis(claim_id)
            manifest_path = claim_file.parent / "evidence_manifest.json"
            evidence_files = json.loads(manifest_path.read_text(encoding="utf-8-sig")) if manifest_path.is_file() else []
            required = list(claim.get("required_evidence", []))
            missing = list(analysis.missing_evidence) if analysis else required
            claim_events = events.get(claim_id, [])
            reviews = [item for item in claim_events if item.get("event_type") == "review"]
            latest_review = reviews[-1] if reviews else None
            highest_signal = None
            if analysis and analysis.signals:
                order = {"high": 2, "review": 1, "info": 0}
                highest_signal = max(analysis.signals, key=lambda item: order[item.severity])
            rows.append({
                "claim_id": claim_id,
                "created_at": claim.get("created_at"),
                "incident_date": claim.get("incident_date"),
                "plate_number": claim.get("plate_number"),
                "analysis_status": analysis.analysis_status if analysis else "not_analyzed",
                "priority": analysis.priority if analysis else "unscored",
                "priority_reason": highest_signal.title if highest_signal else (
                    "Chưa chạy phân tích" if analysis is None else "Chưa có cờ tự động nổi bật"
                ),
                "research_risk_score": analysis.research_risk_score if analysis else None,
                "risk_score_available": bool(analysis and analysis.research_risk_score is not None),
                "required_evidence_count": len(required),
                "present_required_count": max(0, len(required) - len(missing)),
                "uploaded_file_count": len(evidence_files),
                "missing_evidence": missing,
                "signal_count": len(analysis.signals) if analysis else 0,
                "high_signal_count": sum(item.severity == "high" for item in analysis.signals) if analysis else 0,
                "review_signal_count": sum(item.severity == "review" for item in analysis.signals) if analysis else 0,
                "latest_decision": latest_review.get("decision") if latest_review else None,
                "latest_reviewer": latest_review.get("reviewer_id") if latest_review else None,
                "latest_event_at": claim_events[-1].get("created_at") if claim_events else None,
                "event_count": len(claim_events),
                "trace_id": analysis.trace_id if analysis else None,
            })
        priority_order = {"high": 0, "review": 1, "normal": 2, "unscored": 3}
        rows.sort(key=lambda row: str(row["created_at"] or ""), reverse=True)
        rows.sort(key=lambda row: priority_order[row["priority"]])
        return rows
