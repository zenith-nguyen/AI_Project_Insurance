# Báo cáo tiến độ lần 2 — Ghi chú trình bày

## 1. Data

Nhóm đã tổ chức dữ liệu theo Bronze/Processed/Artifacts/Reports, lập registry bảy nguồn và lưu manifest/checksum. CORD, FUNSD, XFUND, SROIE và sample RVL-CDIP đã được intake. MIDV được đăng ký nhưng hoãn tải lớn theo phạm vi hiện tại.

Audit tự động hoàn chỉnh xác nhận CORD, FUNSD canonical, XFUND và RVL-CDIP sample đều PASS. Audit đã phát hiện vấn đề thực thay vì chỉ kiểm tra số file: SROIE corrected mirror có tám ảnh trùng tuyệt đối giữa train và test. Chính sách khắc phục là giữ test, bỏ bản train trùng và tạo validation từ train sạch. FUNSD có hai cây lưu trữ cùng bộ 199 mẫu; audit chọn một canonical root thay vì đếm sai 398 mẫu. Processed split dùng group split theo SHA-256 để một ảnh và các bản sao của nó luôn ở cùng split.

## 2. Baseline và evaluation v1

Nhánh ảnh xe đã hoàn tất quy trình baseline/candidate/final-test:

- YOLOv8n-seg validation mask mAP50-95: 0.5175.
- YOLOv8s-seg validation mask mAP50-95: 0.5284.
- Candidate tăng 0.0109 và đạt quy tắc chọn đặt trước.
- YOLOv8s-seg final-test mask mAP50-95: 0.5140 trên 419 ảnh và 931 instances.
- Checkpoint được khóa bằng SHA-256; final test có execution record và không chạy lần hai.

Nhánh chứng từ đã hoàn tất validation v1 nhưng chưa tuyên bố model production. DiT independent validation đạt macro-F1 0,9283. PaddleOCR là baseline còn yếu với CER 0,4097/WER 0,5592. LayoutLMv3 đạt field micro-F1 0,9214 so với isolated rule 0,6834 và được chọn trên validation; final test vẫn khóa.

## 3. Metrics và lỗi chính

CarDD mạnh ở glass shatter, lamp broken và tire flat; yếu hơn ở crack, dent và scratch. Đây là giới hạn cần nêu trong model card, không che bằng metric trung bình.

Document metrics đã khóa trước khi chạy:

- Classification: macro-F1, balanced accuracy, per-class F1.
- OCR: CER, WER, exact match.
- KIE: field/entity precision, recall, micro-F1, macro-F1.
- Data quality: corrupt rate, exact/near duplicate rate, split leakage.

Consistency và NetworkX point-in-time demo đều PASS. Đây là bằng chứng code/contract chạy đúng trên synthetic data, chưa phải metric phát hiện gian lận.

## 4. Leakage, license và giới hạn

- Test không dùng để chọn model.
- Public datasets không đại diện đầy đủ cho chứng từ bảo hiểm Việt Nam.
- FUNSD/XFUND và RVL-CDIP cần legal review trước mục đích thương mại.
- PII review vẫn là cổng bắt buộc.
- Production gate đang khóa cho tới khi có dữ liệu thật, API monitoring và human review workflow.

## 5. Kiến trúc sản phẩm dự kiến

Ảnh xe đi qua YOLO segmentation. Chứng từ đi qua document classifier, OCR và KIE. Hai nhánh chỉ hợp nhất bằng `claim_id` hợp lệ; sau đó mới tạo đặc trưng đồ thị NetworkX và điểm kiểm tra nhất quán. API trả kết quả, bằng chứng và cảnh báo cho UI; quyết định nghiệp vụ rủi ro cao có human review.

## 6. Công việc kế tiếp

1. Review và chạy LayoutLMv3 final test đúng một lần sau khi protocol được đóng.
2. Đăng ký model/checkpoint/schema/metric và đóng gói inference ngoài notebook.
3. Tạo FastAPI + UI reviewer tối thiểu có `claim_id`, evidence và audit trail.
4. Thu thập golden set bảo hiểm thật và graph entity-edge có timestamp.
5. Kiểm thử end-to-end, security/load, UAT và pilot trước go-live.
