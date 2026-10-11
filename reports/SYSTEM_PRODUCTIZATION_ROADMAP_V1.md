# Lộ trình từ dữ liệu đến sản phẩm v1

Ngày cập nhật: 2026-10-10

## Trạng thái hiện tại

- Nhánh ảnh CarDD: đã khóa YOLOv8s-seg, hoàn tất final test đúng một lần và có checkpoint kiểm chứng bằng SHA-256.
- Nhánh chứng từ: đã intake/audit CORD v2, FUNSD canonical, XFUND, SROIE và RVL-CDIP sample 1.600 ảnh. SROIE processed group split đã PASS với exact overlap bằng 0. DiT, PaddleOCR và rule KIE đã có validation metric; LayoutLMv3 v2 đã chặn mapping không đạt, bản v3 chờ train. MIDV hoãn theo scope.
- Nhánh đồ thị: mới ở mức hợp đồng tích hợp; chưa tạo graph feature khi chưa có thực thể và quan hệ bảo hiểm thật.

## Kiến trúc mục tiêu

```text
Ảnh xe ──> Damage segmentation ───────────────┐
                                               │
Chứng từ ─> Document type ─> OCR ─> KIE ──────┼─> Claim feature store
                                               │        │
Quan hệ claim/customer/vehicle/provider ─> Graph ┘        v
                                                Rules + risk model
                                                        │
                                                        v
                                               FastAPI inference API
                                                        │
                                                        v
                                                   Web/mobile UI
```

Các nhánh chỉ hợp nhất khi có `claim_id` hợp lệ. Dataset công khai chỉ dùng để huấn luyện trước, kiểm thử thuật toán hoặc xây baseline; không ghép từng dòng với CarDD.

## Các cổng thực hiện

### G0 — Data intake

- Lưu dữ liệu gốc bất biến trong Bronze.
- Ghi source, version, license, checksum và run record.
- Kết quả hiện tại: hoàn tất registry/intake cho các nguồn trong scope; CORD, FUNSD, XFUND, SROIE và RVL-CDIP sample đã audit file thật.

### G1 — Data audit

- Kiểm tra file hỏng, PII, trùng và near-duplicate.
- Kiểm tra overlap giữa train/validation/test theo document identity.
- Lập data dictionary và mapping nhãn cho từng task.
- Chỉ nguồn có trạng thái `audit_passed` mới được chuyển sang Processed.

### G2 — Baseline chứng từ

Không huấn luyện một mô hình duy nhất cho mọi việc. Tách ba task:

1. Document classification: phân biệt receipt, invoice, form, ID và loại chứng từ bảo hiểm.
2. OCR: đo CER/WER và tốc độ; ưu tiên baseline pretrained/API trước khi fine-tune.
3. Key Information Extraction: trích xuất field và bounding box; đo precision, recall, F1 theo field.

Mỗi task có train/validation/test riêng và model card riêng.

### G3 — Dữ liệu bảo hiểm thật

- Định nghĩa schema chuẩn: `claim_id`, document type, field name, value, confidence, source page và bounding box.
- Gắn nhãn một tập nhỏ có kiểm soát trước khi mở rộng.
- Che hoặc mã hóa PII trước khi đưa vào môi trường phát triển.
- Đánh giá domain shift giữa dữ liệu công khai và chứng từ Việt Nam.

### G4 — NetworkX và risk model

- Node ban đầu: claim, customer, policy, vehicle, repair shop, invoice, bank account, phone và address.
- Edge phải có timestamp và nguồn chứng minh.
- Feature v1: degree, số thực thể dùng chung, connected component, khoảng cách tới claim rủi ro, cycle và burst theo thời gian.
- Baseline risk model dùng feature bảng và rule; chỉ cân nhắc GNN khi đã có graph thật đủ lớn và nhãn đáng tin cậy.

### G5 — Model packaging và API

- Checkpoint được đăng ký bằng tên, version, SHA-256, schema input/output và metrics.
- Viết inference module độc lập notebook.
- FastAPI nhận request, gọi image/document/graph services và trả JSON có confidence, version và trace ID.
- Docker image cố định dependency; secrets lấy từ environment hoặc secret manager.

### G6 — UI/MVP

- UI tạo claim hoặc nhập `claim_id`.
- Upload ảnh tổn thất và chứng từ.
- Hiển thị mask, loại hư hỏng, field trích xuất và cảnh báo nhất quán.
- Cho người dùng sửa kết quả; sửa đổi được ghi thành feedback, không tự động đưa thẳng vào training.
- Màn hình reviewer hiển thị nguồn, confidence và audit trail.

### G7 — Kiểm thử trước go-live

- Unit/integration/API contract tests.
- Golden set end-to-end không dùng trong training.
- Latency, throughput, file-size limit, malformed file và security tests.
- Shadow hoặc pilot với người dùng nội bộ.
- Theo dõi false positive/negative theo class, drift dữ liệu, lỗi OCR và tỷ lệ người dùng phải sửa.

### G8 — Go-live có kiểm soát

- Triển khai canary hoặc theo nhóm người dùng.
- Có rollback về model/version trước.
- Không tự động từ chối claim chỉ dựa trên model v1; model cung cấp bằng chứng và đề xuất để reviewer quyết định.
- Lập lịch audit, retraining và phê duyệt model mới.

## Thứ tự triển khai tiếp theo

1. Rerun SROIE processed group split để xác minh overlap bằng 0.
2. Dùng schema và ground-truth policy v1 đã soạn để chuẩn hóa task chứng từ.
3. Xây baseline OCR/KIE/classification trên validation, chưa mở test cuối.
4. Chuẩn hóa inference code cho checkpoint CarDD hiện tại.
5. Tạo FastAPI contract và một UI demo dùng model thật.
6. Bổ sung dữ liệu claim thật có `claim_id`, sau đó xây graph feature.
7. Chạy end-to-end test, pilot, quan sát và mới quyết định go-live.

