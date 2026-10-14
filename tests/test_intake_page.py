from fastapi.testclient import TestClient

from src.api.app import app


def test_intake_page_exposes_claim_and_evidence_workflow():
    response = TestClient(app).get("/intake")
    assert response.status_code == 200
    assert "Gửi hồ sơ để kiểm tra" in response.text
    assert "Phân tích hồ sơ" in response.text
    assert "Dùng hồ sơ mẫu" in response.text
    assert "Feature bảng dạng JSON" not in response.text
    assert "/claims/${claimId}/intake" in response.text
    assert "/claims/${claimId}/evidence" in response.text
    assert "/claims/${claimId}/analyze" in response.text
