# 06 — Vận hành và xử lý lỗi

Kiểm tra theo thứ tự:

1. `GET /health`: API chạy và mode là `fixture` hay `live`.
2. `GET /readiness`: module nào active và lý do module chưa chạy.
3. `runtime/readiness.json`: artifact, hash và dependency trên máy.
4. `GET /version`: model version/metric công khai.
5. `trace_id`: liên kết analysis, review và correction.

Các lỗi thường gặp:

- `404`: claim/evidence chưa tồn tại hoặc chưa intake.
- `409`: claim trùng hoặc review trước khi analyze.
- `422`: sai schema, loại file, chữ ký file, guided-capture step hoặc đường dẫn evidence không hợp lệ.
- `partial`: risk score có thể vẫn dùng để xếp hàng nhưng phải đọc module thiếu.
- `blocked`: chưa đủ đầu vào chấm risk.

Không tự retry upload nhiều lần vì có thể tạo bản ghi bằng chứng trùng. Không sửa model registry để bỏ qua lỗi hash.

## Xem hàng đợi và lịch sử

Mở `http://127.0.0.1:8000/dashboard` để xem toàn bộ claim trên máy demo. Nút **Mở hồ sơ** vào workbench; nút **Lịch sử** mở thẳng tab audit của claim. Sau khi bấm **Lưu quyết định**, workbench tải lại nhật ký và mở tab audit.

Trong live mode, dữ liệu claim nằm dưới `runtime/claims/{claim_id}/`; mọi review và correction được append vào `runtime/audit/reviews.jsonl`. Có thể đối chiếu một hành động bằng `claim_id`, `trace_id`, `reviewer_id` và `created_at`. Không chỉnh trực tiếp file JSONL khi server đang chạy.

Dashboard này là giao diện vận hành research local, chưa phải admin production. Trước khi triển khai nội bộ cần đăng nhập, role reviewer/admin, database transaction, phân trang, backup, retention và audit bất biến.

