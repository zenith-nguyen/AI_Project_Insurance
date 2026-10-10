# Hợp đồng tích hợp chứng từ với hồ sơ bồi thường v1

**Ngày:** 10/10/2026  
**Trạng thái:** schema đề xuất; chưa có dữ liệu claim-document thật để kiểm chứng

## Nguyên tắc nối dữ liệu

Dataset công khai chỉ dùng để huấn luyện hoặc đánh giá module chứng từ. Chúng không được ghép trực tiếp với bảng fraud hoặc CarDD. Khi có dữ liệu nghiệp vụ, mỗi tài liệu phải mang `claim_id` thật từ hệ thống nguồn và một `document_id` ổn định.

Quan hệ tối thiểu:

```text
claim 1 ── N claim_document 1 ── N document_page 1 ── N extracted_field
                       │
                       └── N consistency_check
```

## Bảng `claim_document`

| Trường | Kiểu đề xuất | Bắt buộc | Ý nghĩa |
|---|---|---:|---|
| `claim_id` | string | Có | Khóa hồ sơ từ hệ thống nghiệp vụ |
| `document_id` | string | Có | ID ổn định của tài liệu trong claim |
| `document_type` | enum/string | Có | invoice, receipt, police_report, id_card, repair_estimate... |
| `source_system` | string | Có | Nguồn tạo hoặc nhận tài liệu |
| `received_at` | timestamp | Có | Thời điểm tài liệu có sẵn cho scoring |
| `relative_path` | string | Có | Vị trí file trong kho kiểm soát truy cập |
| `sha256` | string | Có | Toàn vẹn và deduplicate |
| `page_count` | integer | Có | Số trang |
| `mime_type` | string | Có | image/jpeg, image/png, application/pdf... |
| `language` | string | Không | Ngôn ngữ dự đoán/xác nhận |
| `pii_classification` | enum | Có | none/low/high/restricted |

Khóa duy nhất: `(claim_id, document_id)`. Không dùng tên file làm khóa.

## Bảng `extracted_field`

| Trường | Kiểu đề xuất | Ý nghĩa |
|---|---|---|
| `claim_id` | string | Khóa nối claim |
| `document_id` | string | Khóa nối tài liệu |
| `page_number` | integer | Trang bắt đầu từ 1 |
| `field_name` | string | total_amount, invoice_date, plate_number... |
| `raw_text` | string | OCR gốc |
| `normalized_value` | string/number/date | Giá trị sau chuẩn hóa |
| `confidence` | float | Độ tin cậy của bước trích xuất |
| `bbox` | array | Vị trí bằng tọa độ chuẩn hóa |
| `model_name` | string | Model/API tạo kết quả |
| `model_version` | string | Version/checkpoint |
| `extracted_at` | timestamp | Thời điểm chạy |
| `evidence_ref` | string | Tham chiếu page/crop để reviewer kiểm tra |

## Bảng `consistency_check`

| Trường | Ví dụ |
|---|---|
| `claim_id` | `CLM-...` |
| `check_name` | `invoice_total_vs_claim_amount` |
| `status` | pass/fail/unknown |
| `observed_value` | Tổng tiền trích xuất |
| `reference_value` | Số tiền khai báo trong claim |
| `difference` | Chênh lệch tuyệt đối/tương đối |
| `reason_code` | missing_field, mismatch, low_confidence... |
| `evidence_document_ids` | Danh sách tài liệu làm bằng chứng |
| `available_at` | Thời điểm check có thể được dùng |

`unknown` phải là trạng thái hợp lệ. Không biến missing hoặc OCR confidence thấp thành tín hiệu fraud mặc định.

## Feature theo thời điểm

- `stage1_intake`: chỉ dùng tài liệu có `received_at <= intake_scored_at`.
- `stage3_complete`: dùng tài liệu đã nhận trước `complete_scored_at`.
- Mỗi feature cần lưu `available_at` để leakage audit kiểm tra.
- Feature graph sau này cũng chỉ dùng node/edge có `event_time <= scored_at`.

## Đầu ra module chứng từ v1

Module chứng từ nên xuất ba nhóm tín hiệu:

1. Chất lượng: thiếu trang, ảnh mờ, OCR confidence thấp, file hỏng.
2. Trường chuẩn hóa: ngày, số tiền, biển số, tên thực thể và mã tài liệu.
3. Kiểm tra nhất quán: chênh lệch giữa tài liệu với claim hoặc giữa nhiều tài liệu.

Các tín hiệu này đi vào scoring/reviewer workflow sau khi schema, timing và ground truth được duyệt. Không dùng dataset công khai để tạo `claim_id` giả hoặc fraud label giả.

## Gate trước khi hợp nhất

- Tỷ lệ `claim_id` hợp lệ và uniqueness đạt ngưỡng đã chốt.
- Không có document hash bị gắn sai sang nhiều claim, trừ trường hợp được giải thích.
- Field dictionary, normalization và missing policy đã khóa.
- OCR/KIE validation hoàn tất trên dữ liệu gần domain mục tiêu.
- PII policy và quyền truy cập được phê duyệt.
- Leakage test theo `received_at`/`available_at` đạt.
- Có sample review cho pass/fail/unknown và error taxonomy.
