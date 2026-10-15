import json
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, PngImagePlugin

pytest.importorskip("networkx")

from src.api.live import LiveClaimService
from src.api.schemas import AnalyzeRequest, ClaimIntakeRequest, CorrectionRequest, ReviewRequest
from src.document.schema import DocumentResult, ExtractedField, OCRToken
from src.media_authenticity import MediaAuthenticityAnalyzer
from src.registry import load_registry


ROOT = Path(__file__).resolve().parents[1]


def service(tmp_path: Path) -> LiveClaimService:
    return LiveClaimService(
        ROOT,
        load_registry(ROOT / "configs/model_registry.v1.yaml"),
        tmp_path / "reviews.jsonl",
        tmp_path / "claims",
    )


def test_golden_claim_runs_real_tabular_rules_and_graph(tmp_path):
    live = service(tmp_path)
    result = live.analyze("CLM-GOLD-001", AnalyzeRequest())

    assert result.mode == "live"
    assert result.claim_id == "CLM-GOLD-001"
    assert result.research_risk_score is not None
    assert result.risk_score_is_probability is False
    assert result.graph_features["shared_entity_count"] == 1
    assert {signal.category for signal in result.signals}.issuperset({"consistency", "relationship"})
    assert result.model_versions == {
        "tabular_risk": "tabular_v1",
        "consistency": "consistency_v2",
        "relationships": "point_in_time_v2",
        "media_authenticity": "media_authenticity_v3",
    }
    assert any("YOLO was not invoked" in warning for warning in result.warnings)
    assert result.module_status["document_pipeline"]["status"] == "completed_precomputed"
    assert result.analysis_status == "partial"
    readiness = live.readiness()
    assert readiness["modules"]["tabular_risk"]["active"] is True
    assert readiness["modules"]["damage_segmentation"]["active"] is False


def test_review_is_persisted_as_jsonl(tmp_path):
    live = service(tmp_path)
    live.analyze("CLM-GOLD-002", AnalyzeRequest())
    record = live.review(
        "CLM-GOLD-002",
        ReviewRequest(
            reviewer_id="reviewer-01",
            decision="request_evidence",
            reason="Cần bổ sung ảnh toàn cảnh",
        ),
    )

    stored = json.loads((tmp_path / "reviews.jsonl").read_text(encoding="utf-8"))
    assert stored["event_type"] == "review"
    assert stored["claim_id"] == record.claim_id
    assert stored["trace_id"] == record.trace_id
    assert live.events("CLM-GOLD-002") == [stored]
    assert live.events("CLM-GOLD-001") == []


def test_field_correction_is_persisted_with_provenance(tmp_path):
    live = service(tmp_path)
    live.analyze("CLM-GOLD-001", AnalyzeRequest())
    record = live.correct(
        "CLM-GOLD-001",
        CorrectionRequest(
            reviewer_id="reviewer-01",
            document_id="DOC-001",
            field_name="total_amount",
            original_value=61680,
            corrected_value=61600,
            reason="Đối chiếu lại ảnh chứng từ gốc",
        ),
    )

    stored = json.loads((tmp_path / "reviews.jsonl").read_text(encoding="utf-8"))
    assert stored["event_type"] == "field_correction"
    assert stored["claim_id"] == record.claim_id
    assert stored["field_name"] == "total_amount"
    assert live.events("CLM-GOLD-001") == [stored]


def test_unknown_golden_claim_is_rejected(tmp_path):
    with pytest.raises(KeyError):
        service(tmp_path).analyze("CLM-GOLD-999", AnalyzeRequest())


def test_all_golden_claim_expectations_are_satisfied(tmp_path):
    live = service(tmp_path)
    for expected_file in sorted((ROOT / "data/golden/claims").glob("*/expected_analysis.json")):
        expected = json.loads(expected_file.read_text(encoding="utf-8"))
        result = live.analyze(expected["claim_id"], AnalyzeRequest())
        categories = {signal.category for signal in result.signals}
        assert result.human_review_required is expected["human_review_required"]
        assert categories.issuperset(expected["required_signal_categories"])


def test_runtime_claim_can_be_intaken_uploaded_and_analyzed(tmp_path):
    live = service(tmp_path)
    class Damage:
        model_name = "yolov8s-seg"
        model_version = "cardd_candidate_v1"
        calls = 0
        def predict(self, image):
            self.calls += 1
            return [{"class_id": 4, "class_name": "scratch", "confidence": 0.8, "box_xyxy": [1, 2, 3, 4], "mask_polygon": None}]

    damage = Damage()
    live.damage = damage
    class Documents:
        pipeline_version = "document-test-v1"
        calls = 0
        def cache_key(self, evidence_sha256):
            return f"document-test-v1:{evidence_sha256}"
        def process(self, path, claim_id, document_id, progress=None):
            self.calls += 1
            return DocumentResult(
                claim_id, document_id, "invoice", 0.92,
                tokens=[OCRToken("Total 61680", 0.9)],
                fields=[ExtractedField("total_amount", "61680", 61680.0, 0.9)],
                model_versions={"classifier": "mock", "ocr": "mock", "kie": "mock"},
                warnings=["kie_model_rule_conflict:total_amount"],
            )

    documents = Documents()
    live.document_runtime = documents
    golden = json.loads((ROOT / "data/golden/claims/CLM-GOLD-001/claim.json").read_text(encoding="utf-8"))
    live.intake(
        "CLM-RUNTIME-001",
        ClaimIntakeRequest(
            claim_amount=golden["claim_amount"],
            incident_date=golden["incident_date"],
            plate_number="51A-12345",
            tabular_features=golden["tabular_features"],
        ),
    )
    image = BytesIO()
    Image.new("RGB", (8, 8), (20, 40, 60)).save(image, format="PNG")
    live.upload("CLM-RUNTIME-001", "image", "damage.png", "image/png", image.getvalue())
    live.upload("CLM-RUNTIME-001", "document", "estimate.pdf", "application/pdf", b"%PDF-1.4 fixture")

    result = live.analyze("CLM-RUNTIME-001", AnalyzeRequest())
    assert result.mode == "live"
    assert result.evidence_completeness == 1.0
    assert {item.kind for item in result.evidence}.issuperset({"claim", "image", "document"})
    assert result.extracted_fields["media_authenticity"][0]["verdict"] == "inconclusive"
    assert result.extracted_fields["damage_detections"][0]["class_name"] == "scratch"
    assert any(item.category == "damage" for item in result.signals)
    assert result.extracted_fields["document_results"][0]["document_type"] == "invoice"
    assert any(item.category == "document" for item in result.signals)
    conflict = next(item for item in result.signals if item.signal_id.endswith("kie-conflict-total_amount"))
    assert conflict.severity == "review"
    assert any("kie_model_rule_conflict:total_amount" in warning for warning in result.warnings)
    image_evidence = next(item for item in result.evidence if item.kind == "image")
    assert image_evidence.content_type == "image/png"
    assert image_evidence.size_bytes == len(image.getvalue())
    assert len(image_evidence.sha256) == 64
    assert damage.calls == 1
    assert documents.calls == 1

    second_image = BytesIO()
    Image.new("RGB", (8, 8), (80, 30, 10)).save(second_image, format="PNG")
    live.upload("CLM-RUNTIME-001", "image", "damage-2.png", "image/png", second_image.getvalue())
    incremental = live.analyze("CLM-RUNTIME-001", AnalyzeRequest())
    assert damage.calls == 2  # old image reused; only the new image invokes YOLO
    assert documents.calls == 1  # unchanged document reused
    assert incremental.module_status["damage_segmentation"]["evidence_cache_hits"] == 1
    assert incremental.module_status["document_pipeline"]["evidence_cache_hits"] == 1

    forced = live.analyze("CLM-RUNTIME-001", AnalyzeRequest(force_recompute=True))
    assert damage.calls == 4
    assert documents.calls == 2
    assert forced.module_status["damage_segmentation"]["evidence_cache_hits"] == 0
    assert forced.module_status["document_pipeline"]["evidence_cache_hits"] == 0


def test_runtime_analysis_survives_service_restart_and_new_evidence_invalidates_it(tmp_path):
    live = service(tmp_path)
    golden = json.loads((ROOT / "data/golden/claims/CLM-GOLD-001/claim.json").read_text(encoding="utf-8"))
    live.intake(
        "CLM-PERSIST-001",
        ClaimIntakeRequest(
            claim_amount=golden["claim_amount"], incident_date=golden["incident_date"],
            plate_number=golden["plate_number"], tabular_features=golden["tabular_features"],
        ),
    )
    first = live.analyze("CLM-PERSIST-001", AnalyzeRequest())
    assert (tmp_path / "claims/CLM-PERSIST-001/analysis.json").is_file()

    restarted = service(tmp_path)
    restored = restarted.get_analysis("CLM-PERSIST-001")
    assert restored is not None
    assert restored.trace_id == first.trace_id
    reused = restarted.analyze("CLM-PERSIST-001", AnalyzeRequest())
    assert reused.trace_id == first.trace_id
    recomputed = restarted.analyze("CLM-PERSIST-001", AnalyzeRequest(force_recompute=True))
    assert recomputed.trace_id != first.trace_id

    image = BytesIO()
    Image.new("RGB", (8, 8), (20, 40, 60)).save(image, format="PNG")
    restarted.upload("CLM-PERSIST-001", "image", "new.png", "image/png", image.getvalue())
    assert restarted.runtime_store.load_analysis("CLM-PERSIST-001") is None
    assert restarted.get_analysis("CLM-PERSIST-001") is None


def test_verified_ai_provenance_becomes_claim_signal(tmp_path):
    live = service(tmp_path)
    golden = json.loads((ROOT / "data/golden/claims/CLM-GOLD-001/claim.json").read_text(encoding="utf-8"))
    live.intake(
        "CLM-RUNTIME-AI",
        ClaimIntakeRequest(
            claim_amount=golden["claim_amount"], incident_date=golden["incident_date"],
            plate_number="51A-12345", tabular_features=golden["tabular_features"],
        ),
    )
    live.media_authenticity = MediaAuthenticityAnalyzer(
        exiftool="",
        c2pa_runner=lambda _: {
            "active_manifest": "urn:test",
            "claim_generator": "test",
            "assertions": [{"digitalSourceType": "trainedAlgorithmicMedia"}],
        },
    )
    image = BytesIO()
    Image.new("RGB", (8, 8), (20, 40, 60)).save(image, format="JPEG")
    live.upload("CLM-RUNTIME-AI", "image", "damage.jpg", "image/jpeg", image.getvalue())

    result = live.analyze("CLM-RUNTIME-AI", AnalyzeRequest())
    signal = next(item for item in result.signals if item.category == "authenticity")
    assert signal.severity == "high"
    assert signal.model_version == "media_authenticity_v3"


def test_missing_documents_keep_tabular_score_and_plate_graph_has_no_shared_entity(tmp_path):
    live = service(tmp_path)
    golden = json.loads((ROOT / "data/golden/claims/CLM-GOLD-001/claim.json").read_text(encoding="utf-8"))
    live.intake(
        "CLM-PARTIAL-001",
        ClaimIntakeRequest(
            claim_amount=golden["claim_amount"], incident_date=golden["incident_date"],
            plate_number=golden["plate_number"], tabular_features=golden["tabular_features"],
        ),
    )

    result = live.analyze("CLM-PARTIAL-001", AnalyzeRequest())

    assert result.analysis_status == "partial"
    assert result.research_risk_score is not None
    assert result.module_status["tabular_risk"]["status"] == "completed"
    assert result.module_status["document_pipeline"]["status"] == "skipped_missing_input"
    assert result.module_status["relationships"]["status"] == "completed"
    assert result.graph_features["data_status"] == "provided"
    assert result.graph_features["shared_entity_count"] == 0
    assert result.graph_features["two_hop_claim_count"] == 0


def test_missing_tabular_features_blocks_score_without_crashing_other_modules(tmp_path):
    live = service(tmp_path)
    live.intake("CLM-BLOCKED-001", ClaimIntakeRequest(tabular_features={}))

    result = live.analyze("CLM-BLOCKED-001", AnalyzeRequest())

    assert result.analysis_status == "blocked"
    assert result.research_risk_score is None
    assert result.module_status["tabular_risk"]["status"] == "blocked_missing_input"
    assert result.module_status["tabular_risk"]["required_field_count"] > 0
    assert result.module_status["tabular_risk"]["provided_field_count"] == 0
    assert result.module_status["tabular_risk"]["missing_field_count"] > 0
    assert set(result.module_status["tabular_risk"]["missing_business_groups"]).issuperset({"policy", "incident"})


def test_stored_analysis_from_older_ui_gets_tabular_explanation_metadata(tmp_path):
    live = service(tmp_path)
    live.intake("CLM-OLD-UI-001", ClaimIntakeRequest(tabular_features={}))
    live.analyze("CLM-OLD-UI-001", AnalyzeRequest())
    analysis_file = tmp_path / "claims/CLM-OLD-UI-001/analysis.json"
    payload = json.loads(analysis_file.read_text(encoding="utf-8"))
    payload["module_status"]["tabular_risk"] = {
        "status": "blocked_missing_input", "reason": "legacy technical error",
    }
    analysis_file.write_text(json.dumps(payload), encoding="utf-8")

    restored = service(tmp_path).get_analysis("CLM-OLD-UI-001")

    assert restored is not None
    assert restored.module_status["tabular_risk"]["missing_field_count"] > 0
    assert restored.module_status["tabular_risk"]["missing_business_groups"]


def test_cross_claim_exact_image_reuse_is_detected_automatically(tmp_path):
    live = service(tmp_path)
    golden = json.loads((ROOT / "data/golden/claims/CLM-GOLD-001/claim.json").read_text(encoding="utf-8"))
    request = ClaimIntakeRequest(
        claim_amount=golden["claim_amount"], incident_date=golden["incident_date"],
        plate_number=golden["plate_number"], tabular_features=golden["tabular_features"],
    )
    live.intake("CLM-REUSE-001", request)
    live.intake("CLM-REUSE-002", request)
    image = BytesIO()
    Image.new("RGB", (24, 24), (30, 80, 120)).save(image, format="JPEG")
    content = image.getvalue()
    live.upload("CLM-REUSE-001", "image", "first.jpg", "image/jpeg", content)
    second = live.upload("CLM-REUSE-002", "image", "second.jpg", "image/jpeg", content)

    report = live.authenticity("CLM-REUSE-002", second.evidence_id)

    assert report.verdict == "review"
    finding = next(item for item in report.findings if item.code == "cross_claim_image_reuse")
    assert finding.severity == "high"
    assert report.image_info["cross_claim_matches"][0]["claim_id"] == "CLM-REUSE-001"
    first_id = json.loads((tmp_path / "claims/CLM-REUSE-001/evidence_manifest.json").read_text(encoding="utf-8"))[0]["evidence_id"]
    refreshed_first = live.authenticity("CLM-REUSE-001", first_id)
    assert refreshed_first.image_info["cross_claim_matches"][0]["claim_id"] == "CLM-REUSE-002"


def test_resized_and_recompressed_image_is_detected_as_near_duplicate(tmp_path):
    live = service(tmp_path)
    golden = json.loads((ROOT / "data/golden/claims/CLM-GOLD-001/claim.json").read_text(encoding="utf-8"))
    request = ClaimIntakeRequest(tabular_features=golden["tabular_features"])
    live.intake("CLM-NEAR-001", request)
    live.intake("CLM-NEAR-002", request)
    base = Image.new("RGB", (160, 120), "white")
    draw = ImageDraw.Draw(base)
    draw.rectangle((12, 18, 86, 94), fill=(22, 95, 150))
    draw.ellipse((92, 25, 148, 82), fill=(210, 75, 50))
    first = BytesIO()
    base.save(first, format="JPEG", quality=95)
    second = BytesIO()
    base.resize((112, 84), Image.Resampling.LANCZOS).save(second, format="JPEG", quality=45)
    live.upload("CLM-NEAR-001", "image", "original.jpg", "image/jpeg", first.getvalue())
    uploaded = live.upload("CLM-NEAR-002", "image", "social-copy.jpg", "image/jpeg", second.getvalue())

    report = live.authenticity("CLM-NEAR-002", uploaded.evidence_id)

    match = report.image_info["cross_claim_matches"][0]
    assert match["claim_id"] == "CLM-NEAR-001"
    assert match["match_type"] == "near_duplicate"


def test_declared_ai_and_editing_software_metadata_are_reported(tmp_path):
    live = service(tmp_path)
    golden = json.loads((ROOT / "data/golden/claims/CLM-GOLD-001/claim.json").read_text(encoding="utf-8"))
    live.intake("CLM-META-001", ClaimIntakeRequest(tabular_features=golden["tabular_features"]))
    image = BytesIO()
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("description", "AI generated with OpenAI image; edited with Adobe Photoshop")
    Image.new("RGB", (32, 32), (30, 70, 110)).save(image, format="PNG", pnginfo=metadata)
    uploaded = live.upload("CLM-META-001", "image", "declared-ai.png", "image/png", image.getvalue())

    report = live.authenticity("CLM-META-001", uploaded.evidence_id)
    codes = {finding.code for finding in report.findings}

    assert "ai_metadata_marker_1" in codes
    assert "editing_software_marker_1" in codes
    assert report.verdict == "review"


def test_relationship_graph_matches_prior_claims_by_hashed_entities(tmp_path):
    live = service(tmp_path)
    golden = json.loads((ROOT / "data/golden/claims/CLM-GOLD-001/claim.json").read_text(encoding="utf-8"))
    common = {"contact_phone": "0909 000 111", "repair_shop": "GARAGE-DEMO-01"}
    live.intake("CLM-LINK-001", ClaimIntakeRequest(
        plate_number="51A-111.11", relationship_entities=common, tabular_features=golden["tabular_features"],
    ))
    live.intake("CLM-LINK-002", ClaimIntakeRequest(
        plate_number="51A-222.22", relationship_entities=common, tabular_features=golden["tabular_features"],
    ))

    result = live.analyze("CLM-LINK-002", AnalyzeRequest())

    assert result.module_status["relationships"]["status"] == "completed"
    assert result.graph_features["shared_entity_count"] == 2
    assert result.graph_features["two_hop_claim_count"] == 1
    assert any(signal.category == "relationship" for signal in result.signals)
    assert result.graph_features["query_entity_display"]["contact_phone"] == "••••0111"
    assert "0909000111" not in json.dumps(result.graph_features, ensure_ascii=False)


def test_relationship_graph_uses_scored_at_for_imported_history(tmp_path):
    live = service(tmp_path)
    common = {"contact_id": "CONTACT-DEMO-01", "repair_shop": "GARAGE-DEMO-01"}
    live.intake("CLM-HISTORY-001", ClaimIntakeRequest(
        scored_at="2026-09-20T09:00:00+07:00", plate_number="51A-111.11", relationship_entities=common,
    ))
    live.intake("CLM-HISTORY-002", ClaimIntakeRequest(
        scored_at="2026-09-22T09:00:00+07:00", plate_number="51A-222.22", relationship_entities=common,
    ))

    result = live.analyze("CLM-HISTORY-002", AnalyzeRequest())

    assert result.graph_features["two_hop_claim_count"] == 1
    assert result.graph_features["related_claim_ids"] == ["CLM-HISTORY-001"]


def test_relationship_graph_scope_prevents_cross_run_contamination(tmp_path):
    live = service(tmp_path)
    shared = {"contact_id": "CONTACT-DEMO-01", "repair_shop": "GARAGE-DEMO-01"}
    live.intake("CLM-RUN-A", ClaimIntakeRequest(
        scored_at="2026-09-20T09:00:00+07:00", plate_number="51A-111.11",
        relationship_entities={**shared, "relationship_scope": "run-a"},
    ))
    live.intake("CLM-RUN-B", ClaimIntakeRequest(
        scored_at="2026-09-21T09:00:00+07:00", plate_number="51A-111.11",
        relationship_entities={**shared, "relationship_scope": "run-b"},
    ))

    result = live.analyze("CLM-RUN-B", AnalyzeRequest())

    assert result.graph_features["related_claim_ids"] == []


def test_admin_queue_reads_persisted_analysis_and_latest_review(tmp_path):
    live = service(tmp_path)
    golden = json.loads((ROOT / "data/golden/claims/CLM-GOLD-001/claim.json").read_text(encoding="utf-8"))
    live.intake("CLM-QUEUE-001", ClaimIntakeRequest(
        plate_number="51A-909.09", tabular_features=golden["tabular_features"], required_evidence=["claim-intake"],
    ))
    live.analyze("CLM-QUEUE-001", AnalyzeRequest())
    live.review("CLM-QUEUE-001", ReviewRequest(
        reviewer_id="reviewer-01", decision="special_review", reason="Kiá»ƒm tra báº±ng chá»©ng bá»• sung",
    ))

    restarted = service(tmp_path)
    row = next(item for item in restarted.list_claims() if item["claim_id"] == "CLM-QUEUE-001")

    assert row["risk_score_available"] is True
    assert row["required_evidence_count"] == 1
    assert row["present_required_count"] == 1
    assert row["latest_decision"] == "special_review"
    assert row["event_count"] == 1
