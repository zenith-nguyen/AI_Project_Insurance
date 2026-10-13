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

