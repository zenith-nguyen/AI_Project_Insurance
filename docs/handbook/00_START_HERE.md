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

Trạng thái hiện tại là **research prototype có luồng end-to-end một phần**. XGBoost, rules, NetworkX, upload, authenticity, review và correction đã nối vào API. YOLO và document pipeline có adapter nhưng máy triển khai phải có checkpoint/dependency đúng hash.

Không đưa raw data, token, PII hoặc checkpoint lớn vào Git. Mọi kết quả phải được hiểu cùng `analysis_status`, `module_status`, `warnings`, model version và evidence reference.

