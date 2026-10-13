from fastapi.testclient import TestClient

from src.api.app import app


def test_intake_page_exposes_claim_and_evidence_workflow():
    response = TestClient(app).get("/intake")
    assert response.status_code == 200
    assert "Nạp hồ sơ để phân tích" in response.text
    assert "Điền toàn bộ dữ liệu mẫu" in response.text
    assert "Tạo mã mới" in response.text
    assert "Demo thông thường dùng bước 1" in response.text
    assert "/claims/${claimId}/intake" in response.text
    assert "/claims/${claimId}/evidence" in response.text
