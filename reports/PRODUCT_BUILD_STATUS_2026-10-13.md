# Trạng thái xây dựng sản phẩm — 2026-10-13

## Người dùng sẽ nhận được sản phẩm gì?

Sản phẩm đang được xây dựng là **Claim Review Workbench**: một màn hình giúp giám định viên mở một hồ sơ, xem mức ưu tiên, đối chiếu ảnh và chứng từ, xem quan hệ với hồ sơ khác, rồi lưu quyết định cùng lý do. AI chỉ sắp xếp và trình bày bằng chứng; con người vẫn quyết định.

## Phần đã chạy nối với nhau

Năm golden claims `CLM-GOLD-001` đến `CLM-GOLD-005` dùng cùng một `claim_id` xuyên suốt dữ liệu bảng, chứng từ, ảnh placeholder, quan hệ và kết quả mong đợi.

Luồng live đầu tiên đã nối:

1. XGBoost checkpoint thật để tạo điểm xếp hạng nghiên cứu.
2. Consistency rules thật để so số tiền, ngày và biển số.
3. NetworkX thật để tính quan hệ tại đúng thời điểm chấm.
4. API trả cùng schema mà prototype fixture đang dùng.
5. Quyết định của người duyệt được ghi vào audit log JSONL.
6. Reviewer có endpoint sửa trường OCR/KIE; giá trị cũ, giá trị mới, lý do, người sửa, `claim_id`, `trace_id` và thời gian được lưu cùng audit log.

## Phần chưa gọi live trong API

- YOLOv8s-seg: đã final test, cần adapter nhận ảnh và artifact store.
- DiT, PaddleOCR và LayoutLMv3: đã có kết quả nghiên cứu; cần adapter xử lý file chứng từ thật.
- Golden claims hiện dùng trường chứng từ đã trích xuất trước và ảnh placeholder. API ghi rõ giới hạn này trong `warnings`.

## Cách chạy cho hai nhóm

Đội UI chạy `scripts/setup_ui.ps1` và `scripts/run_ui.ps1`; không cần data, Drive hoặc GPU. Người phụ trách ML/backend chạy `scripts/setup_live.ps1` và `scripts/run_live.ps1`; máy cần bundle XGBoost đúng SHA-256 trong model registry.

## Mốc tiếp theo

1. Cho prototype render toàn bộ dữ liệu trả về từ API thay vì chữ tĩnh.
2. Thêm document adapter theo chuỗi DiT → PaddleOCR → LayoutLMv3.
3. Thêm YOLO adapter và binary image fixtures.
4. Nối form sửa OCR/KIE trên UI vào correction endpoint đã có.
5. Chạy golden end-to-end tests, latency test và kiểm tra dữ liệu nhạy cảm.

Đây là research prototype có thể demo luồng tích hợp. Nó chưa phải hệ thống production và chưa được phép tự động từ chối hồ sơ.
