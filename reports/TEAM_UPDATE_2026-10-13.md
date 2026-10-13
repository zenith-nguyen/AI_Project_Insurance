# Cập nhật cho team — 13/10/2026

## Báo cáo tiến độ 2 đã hoàn thành chưa?

**Đã hoàn thành.** Gói v8 ngày 12/10 đã đáp ứng phạm vi Data + Baseline + Evaluation v1. Ngày 13/10 nhóm hoàn tất thêm LayoutLMv3 final test, nên v9 chỉ cập nhật bằng chứng mới này, model registry và kế hoạch bước tiếp theo. Các kết quả Data Audit, XGBoost, CarDD, DiT, OCR, API contract và prototype trong v8 vẫn giữ nguyên.

## Kết quả mới

LayoutLMv3 trích xuất `date` và `total` được đánh giá trên 361 ảnh SROIE final test:

- Field micro-F1: **0,8659**.
- Date F1: **0,8320**.
- Total F1: **0,8995**.
- Validation trước đó: **0,9214**.
- Checkpoint: `checkpoint-264`.
- Inference chạy một lần; test không được đọc lại trong quá trình phục hồi metric.

Kết quả này đóng gate nghiên cứu của nhánh KIE. Không tiếp tục chỉnh model theo final test.

## Sản phẩm hiện tại

Nhóm đang xây **Claim Review Workbench**, một màn hình hỗ trợ nhân viên bảo hiểm xem hồ sơ và bằng chứng. Hệ thống gồm nhiều công cụ:

- XGBoost sắp xếp hồ sơ cần ưu tiên xem.
- YOLO đánh dấu vùng hư hỏng trên ảnh xe.
- DiT nhận biết loại chứng từ.
- PaddleOCR đọc chữ và vị trí.
- LayoutLMv3 lấy ngày và tổng tiền.
- Rules đối chiếu thông tin giữa các nguồn.
- NetworkX hiển thị các hồ sơ có thực thể dùng chung.

Các module hiện đã chạy riêng và có metric. API/UI fixture cũng chạy được. Phần còn thiếu là nối checkpoint thật vào API và kiểm thử một claim xuyên suốt toàn hệ thống.

## Việc tiếp theo

1. Tạo 5–10 golden claims giả lập hoặc đã ẩn danh, mỗi claim có cùng `claim_id` ở dữ liệu bảng, ảnh, chứng từ và graph.
2. Viết live adapters để API gọi model thật, giữ nguyên JSON contract cho đội UI.
3. Nối UI vào API và kiểm thử luồng: mở claim → xem bằng chứng → sửa kết quả → ghi quyết định.
4. Cải thiện OCR, các lớp ảnh yếu và XGBoost bằng validation/dữ liệu mới; không tối ưu theo final tests đã khóa.
5. Chỉ pilot sau khi có dữ liệu bảo hiểm Việt Nam hợp lệ, security/load test và UAT.

## Cách nói ngắn khi trình bày

> Nhóm đã hoàn thành Data + Baseline + Evaluation v1 và có prototype hỗ trợ duyệt claim. Các model đã được đánh giá riêng; LayoutLMv3 vừa đóng final test với field F1 0,8659. Giai đoạn kế tiếp là tích hợp model thật qua API, tạo golden claims xuyên suốt và nối UI để kiểm thử end-to-end. Đây vẫn là hệ thống hỗ trợ con người, chưa phải sản phẩm tự động kết luận gian lận.
