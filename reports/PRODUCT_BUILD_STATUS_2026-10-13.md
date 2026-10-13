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
7. Trang `/intake` tạo hồ sơ và tải ảnh/PDF lên kho runtime; API kiểm loại tệp, kích thước, chữ ký nội dung, SHA-256 và gắn mọi bằng chứng với `claim_id`.
8. `media_authenticity_v2` chạy tự động khi upload: đọc EXIF/XMP, hỗ trợ ExifTool/C2PA, ghi rõ trạng thái SynthID, trích xuất pixel features và phát hiện ảnh tái sử dụng giữa các claim bằng SHA-256/perceptual hash.
9. Luồng phân tích đã chịu được dữ liệu thiếu: đủ feature bảng thì vẫn trả risk score; thiếu chứng từ, ảnh hoặc graph được ghi `partial`. Thiếu feature bắt buộc của XGBoost được ghi `blocked`, không làm toàn API sập. Graph chưa được cung cấp không còn bị hiểu nhầm thành “0 quan hệ”.
10. Intake đã có guided capture 10 phút với ba bước theo thứ tự và một góc chụp ngẫu nhiên. Ảnh được gắn session/step/hash; bước lặp bị từ chối. Assurance hiện là `guided_unverified`, chưa thay thế mobile attestation.

## Phần đã có adapter live, cần artifact/dependency trên máy chạy

- YOLOv8s-seg: adapter nhận ảnh, kiểm SHA-256 và chuẩn hóa box/mask đã hoàn thành; tự bật khi checkpoint và `ultralytics` có trên máy.
- DiT → PaddleOCR → LayoutLMv3: adapter ảnh/PDF, kiểm tree hash checkpoint, OCR, KIE và consistency đã hoàn thành; tự bật khi checkpoint cùng dependency có trên máy.
- Golden claims hiện dùng trường chứng từ đã trích xuất trước và ảnh placeholder. API ghi rõ giới hạn này trong `warnings`.

## Cách chạy cho hai nhóm

Đội UI chạy `scripts/setup_ui.ps1` và `scripts/run_ui.ps1`; không cần data, Drive hoặc GPU. Người phụ trách ML/backend chạy `scripts/setup_live.ps1` và `scripts/run_live.ps1`; máy cần bundle XGBoost đúng SHA-256 trong model registry.

## Mốc tiếp theo

1. Chép hai checkpoint đã khóa từ artifact store vào máy tích hợp và chạy golden binary fixtures qua adapter thật.
2. Hiển thị mask YOLO, OCR box và provenance chi tiết trực tiếp trên UI.
3. Thu thập benchmark media-authenticity theo manifest group-safe đã có; khóa threshold trên validation rồi đo test theo generator và từng loại biến đổi.
4. Đo latency/load, kiểm tra dữ liệu nhạy cảm, authentication và phân quyền.
5. Thực hiện domain validation Việt Nam và UAT với người dùng nghiệp vụ.

Đây là research prototype có thể demo luồng tích hợp. Nó chưa phải hệ thống production và chưa được phép tự động từ chối hồ sơ.
