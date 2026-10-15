from fastapi.testclient import TestClient

from src.api.app import app


def test_intake_page_exposes_claim_and_evidence_workflow():
    response = TestClient(app).get("/intake")
    assert response.status_code == 200
    assert "Gửi hồ sơ để kiểm tra" in response.text
    assert "Phân tích hồ sơ" in response.text
    assert "Dùng hồ sơ mẫu" in response.text
    assert "Feature bảng dạng JSON" not in response.text
    assert 'src="/intake.js?v=20261015f"' in response.text
    script = TestClient(app).get("/intake.js")
    assert script.status_code == 200
    assert "/claims/${claimId}/intake" in script.text
    assert "/claims/${claimId}/evidence" in script.text
    assert "/claims/${claimId}/analysis-jobs" in script.text
    assert "Tạo yêu cầu chụp 3 góc" in response.text
