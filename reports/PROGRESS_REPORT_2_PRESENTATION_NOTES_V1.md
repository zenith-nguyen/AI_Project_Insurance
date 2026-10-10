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

Nhánh chứng từ chưa tuyên bố model cuối. Baseline protocol gồm DiT cho document classification, PaddleOCR cho OCR, rule-based extraction làm KIE baseline và LayoutLMv3 làm candidate nghiên cứu.

## 3. Metrics và lỗi chính

CarDD mạnh ở glass shatter, lamp broken và tire flat; yếu hơn ở crack, dent và scratch. Đây là giới hạn cần nêu trong model card, không che bằng metric trung bình.

Document metrics đã khóa trước khi chạy:

- Classification: macro-F1, balanced accuracy, per-class F1.
- OCR: CER, WER, exact match.
- KIE: field/entity precision, recall, micro-F1, macro-F1.
- Data quality: corrupt rate, exact/near duplicate rate, split leakage.

## 4. Leakage, license và giới hạn

- Test không dùng để chọn model.
- Public datasets không đại diện đầy đủ cho chứng từ bảo hiểm Việt Nam.
- FUNSD/XFUND và RVL-CDIP cần legal review trước mục đích thương mại.
- PII review vẫn là cổng bắt buộc.
- Production gate đang khóa cho tới khi có dữ liệu thật, API monitoring và human review workflow.

## 5. Kiến trúc sản phẩm dự kiến

Ảnh xe đi qua YOLO segmentation. Chứng từ đi qua document classifier, OCR và KIE. Hai nhánh chỉ hợp nhất bằng `claim_id` hợp lệ; sau đó mới tạo đặc trưng đồ thị NetworkX và điểm kiểm tra nhất quán. API trả kết quả, bằng chứng và cảnh báo cho UI; quyết định nghiệp vụ rủi ro cao có human review.

## 6. Công việc kế tiếp

1. Hoàn tất audit XFUND/RVL và SROIE processed split.
2. Chạy classification/OCR/KIE baseline trên train/validation đã khóa.
3. Lập error analysis và model selection matrix bằng kết quả thật.
4. Đóng gói inference pipeline thành API, thêm schema `claim_id`, logging và version metadata.
5. Kết nối UI thử nghiệm, kiểm thử tích hợp và UAT trước go-live.
