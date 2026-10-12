from fastapi.testclient import TestClient

from src.api.app import app


client = TestClient(app)


def test_fixture_claim_lifecycle_and_human_review_contract():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "mode": "fixture", "product_version": "research-v1"}

    version = client.get("/version").json()
    assert version["models"]["damage_segmentation"]["status"] == "final_test_complete"

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


def test_review_requires_analysis_first():
    response = client.post(
        "/claims/NOT-ANALYZED/review",
        json={"reviewer_id": "reviewer-01", "decision": "special_review", "reason": "Có tín hiệu cần xác minh thêm"},
    )
    assert response.status_code == 409
