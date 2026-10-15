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

## Khi dashboard báo `api.listClaims is not a function`

Đây là lỗi cache giao diện: trình duyệt đã giữ `api-client.js` cũ trong khi tải `dashboard.js` mới. Bản hiện tại đã gắn version cho cả hai file và HTTP response UI dùng `Cache-Control: no-store`. Sau khi cập nhật code, tải lại đúng một lần bằng `Ctrl+F5`; không cần xóa dữ liệu claim hoặc chạy lại model.

## Bộ test demo nghiệp vụ

Script `scripts/build_business_demo_pack.py` tạo bộ test có thứ tự, hướng dẫn nhập, kết quả kỹ thuật, giá trị nghiệp vụ, hành động và tiêu chí PASS. Bộ đã khóa ngày 15/10/2026 trên máy demo nằm tại `D:\My Dowload\00_TEST_CLAIM_REVIEW_BUSINESS_FINAL_2026-10-15` và ZIP cùng tên. Chỉ mở `http://127.0.0.1:8000/`, sau đó dùng menu trái để đi giữa Dashboard, Nạp hồ sơ và Workbench.

