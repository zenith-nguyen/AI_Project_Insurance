from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image
from uuid import uuid4

from src.api.app import app


client = TestClient(app)


def test_browser_api_client_is_served_by_the_backend():
    response = client.get("/api-client.js")
    assert response.status_code == 200
    assert "export class ClaimReviewClient" in response.text
    workbench = client.get("/")
    assert workbench.status_code == 200
    assert 'src="/workbench.js"' in workbench.text
    assert "Quyết định của người duyệt" in workbench.text
    assert "DIỄN GIẢI NGHIỆP VỤ" in workbench.text
    assert "Phát hiện → ý nghĩa → hành động" in workbench.text
    script = client.get("/workbench.js")
    assert script.status_code == 200
    assert 'import {ClaimReviewClient, ClaimApiError} from "/api-client.js"' in script.text
    assert "evidenceContentUrl" in script.text
    assert "addOverlay" in script.text


def test_fixture_claim_lifecycle_and_human_review_contract():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "mode": "fixture", "product_version": "research-v1"}

    version = client.get("/version").json()
    assert version["models"]["damage_segmentation"]["status"] == "final_test_complete"
    readiness = client.get("/readiness").json()
    assert readiness["mode"] == "fixture"
    assert readiness["fully_live"] is False

    created = client.post(
        "/claims/CLM-TEST-001/analyze",
        json={"claim_amount": 16000000, "incident_date": "2026-10-11", "plate_number": "51H-123.42"},
    )
    assert created.status_code == 200
    analysis = created.json()
    assert analysis["claim_id"] == "CLM-TEST-001"
    assert analysis["human_review_required"] is True
    assert analysis["risk_score_is_probability"] is False
    assert analysis["extracted_fields"]["claim_amount"] == 16000000

    fetched = client.get("/claims/CLM-TEST-001/analysis")
    assert fetched.status_code == 200
    assert fetched.json()["trace_id"] == analysis["trace_id"]

    review = client.post(
        "/claims/CLM-TEST-001/review",
        json={"reviewer_id": "reviewer-01", "decision": "request_evidence", "reason": "Thiếu ảnh toàn cảnh phía sau xe"},
    )
    assert review.status_code == 200
    assert review.json()["trace_id"] == analysis["trace_id"]

    correction = client.post(
        "/claims/CLM-TEST-001/corrections",
        json={
            "reviewer_id": "reviewer-01",
            "document_id": "DOC-001",
            "field_name": "plate_number",
            "original_value": "51H-123.42",
            "corrected_value": "51H-123.43",
            "reason": "Đối chiếu với ảnh đăng ký xe",
        },
    )
    assert correction.status_code == 200
    assert correction.json()["trace_id"] == analysis["trace_id"]
    events = client.get("/claims/CLM-TEST-001/events")
    assert events.status_code == 200
    assert [event["event_type"] for event in events.json()] == ["review", "field_correction"]


def test_review_requires_analysis_first():
    response = client.post(
        "/claims/NOT-ANALYZED/review",
        json={"reviewer_id": "reviewer-01", "decision": "special_review", "reason": "Có tín hiệu cần xác minh thêm"},
    )
    assert response.status_code == 409

    correction = client.post(
        "/claims/NOT-ANALYZED/corrections",
        json={
            "reviewer_id": "reviewer-01",
            "document_id": "DOC-001",
            "field_name": "total_amount",
            "original_value": 100,
            "corrected_value": 120,
            "reason": "Đối chiếu lại chứng từ gốc",
        },
    )
    assert correction.status_code == 409


def test_claim_intake_and_evidence_upload_contract():
    claim_id = f"CLM-UPLOAD-{uuid4().hex[:8]}"
    intake = client.post(
        f"/claims/{claim_id}/intake",
        json={"claim_amount": 12000000, "incident_date": "2026-10-13", "plate_number": "51A-12345"},
    )
    assert intake.status_code == 201
    binary = BytesIO()
    Image.new("RGB", (8, 8), (20, 40, 60)).save(binary, format="PNG")
    upload = client.post(
        f"/claims/{claim_id}/evidence",
        data={"kind": "image"},
        files={"file": ("damage.png", binary.getvalue(), "image/png")},
    )
    assert upload.status_code == 201
    assert upload.json()["claim_id"] == claim_id
    assert upload.json()["sha256"]
    assert upload.json()["authenticity_verdict"] in {"inconclusive", "review"}
    content = client.get(f"/claims/{claim_id}/evidence/{upload.json()['evidence_id']}/content")
    assert content.status_code == 200
    assert content.content == binary.getvalue()
    assert content.headers["cache-control"] == "private, no-store"
    assert content.headers["x-content-type-options"] == "nosniff"
    authenticity = client.get(
        f"/claims/{claim_id}/evidence/{upload.json()['evidence_id']}/authenticity"
    )
    assert authenticity.status_code == 200
    assert authenticity.json()["verdict"] in {"inconclusive", "review"}


def test_guided_capture_session_links_ordered_images_to_claim():
    claim_id = f"CLM-CAPTURE-{uuid4().hex[:8]}"
    assert client.post(f"/claims/{claim_id}/intake", json={}).status_code == 201
    session_response = client.post(f"/claims/{claim_id}/capture-sessions")
    assert session_response.status_code == 201
    session = session_response.json()
    assert session["status"] == "issued"
    assert session["assurance_level"] == "guided_unverified"
    assert len(session["instructions"]) == 3

    for instruction in session["instructions"]:
        binary = BytesIO()
        Image.new("RGB", (12, 12), (instruction["step"] * 20, 40, 60)).save(binary, format="JPEG")
        upload = client.post(
            f"/claims/{claim_id}/evidence",
            data={
                "kind": "image", "capture_session_id": session["session_id"],
                "challenge_step": str(instruction["step"]),
            },
            files={"file": (f"step-{instruction['step']}.jpg", binary.getvalue(), "image/jpeg")},
        )
        assert upload.status_code == 201
        assert upload.json()["capture_session_id"] == session["session_id"]
        assert upload.json()["challenge_step"] == instruction["step"]
        assert upload.json()["capture_assurance"] == "guided_unverified"

    duplicate = client.post(
        f"/claims/{claim_id}/evidence",
        data={"kind": "image", "capture_session_id": session["session_id"], "challenge_step": "1"},
        files={"file": ("duplicate.jpg", binary.getvalue(), "image/jpeg")},
    )
    assert duplicate.status_code == 422
