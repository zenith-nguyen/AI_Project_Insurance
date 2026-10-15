# 00 — Bắt đầu tại đây

Đây là bộ hướng dẫn chính thức cho **Claim Review Workbench**. Sản phẩm hỗ trợ giám định viên xếp hàng ưu tiên, đọc ảnh/chứng từ, kiểm tra tính nhất quán và quan hệ giữa hồ sơ, rồi lưu quyết định có audit trail. AI không tự kết luận gian lận và không tự từ chối bồi thường.

Đọc theo thứ tự:

1. `01_PRODUCT_AND_USER_FLOW.md` — sản phẩm là gì và người dùng thao tác thế nào.
2. `02_INSTALLATION_AND_QUICKSTART.md` — chạy bản UI hoặc backend live.
3. `03_API_AND_UI_INTEGRATION.md` — contract dành cho đội UI/backend.
4. `04_MODELS_METRICS_AND_LIMITATIONS.md` — model, chỉ số và giới hạn.
5. `05_DATA_ARTIFACTS_AND_GOVERNANCE.md` — data, checkpoint, hash và quyền truy cập.
6. `06_OPERATIONS_AND_TROUBLESHOOTING.md` — vận hành và xử lý lỗi.
7. `07_RELEASE_SECURITY_AND_UAT.md` — điều kiện pilot/phát hành.
8. `08_DEFINITION_OF_DONE.md` — tiêu chí kết thúc dự án và các mức release.

Trạng thái hiện tại là **Technical PoC có một golden binary run end-to-end PASS**. XGBoost, rules v2, NetworkX v2, upload, authenticity, YOLO, DiT → PaddleOCR → LayoutLMv3, review và correction đã chạy chung một `claim_id` trên máy tích hợp. Research handoff vẫn chờ bộ 20–50 golden claims đúng miền và các sign-off thủ công; pilot vẫn chờ validation Việt Nam, security/load test và UAT.

Xem trạng thái mới nhất ở `reports/PROGRESS_STATUS_LATEST_2026-10-15.md`. Dashboard đọc cùng nguồn machine-readable `configs/model_improvement_status.v1.yaml`, nên tiến độ kỹ thuật, giá trị nghiệp vụ, gate và blocker được trình bày thống nhất.

Không đưa raw data, token, PII hoặc checkpoint lớn vào Git. Mọi kết quả phải được hiểu cùng `analysis_status`, `module_status`, `warnings`, model version và evidence reference.

