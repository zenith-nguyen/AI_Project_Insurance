# Quy trình benchmark OCR chứng từ bảo hiểm Việt Nam v1

## Mục đích

Quy trình này biến 50–100 trang chứng từ có quyền sử dụng thành một validation set có thể kiểm toán. Nó đo chất lượng và tốc độ của PaddleOCR trên đúng miền nghiệp vụ, không dùng ba hồ sơ demo để tuyên bố độ chính xác.

Tạo workspace private có sẵn biểu mẫu quyền sử dụng và adjudication bằng `scripts/create_vietnamese_ocr_labeling_kit.py --output <thu_muc_private>`.

## Dữ liệu tối thiểu

Mỗi trang là một dòng JSONL với các trường:

| Trường | Ý nghĩa nghiệp vụ |
|---|---|
| `sample_id` | Mã trang ẩn danh, duy nhất |
| `split` | Phải là `validation`; không dùng để train |
| `image_path` | Đường dẫn tương đối tới ảnh trong kho private/DVC |
| `image_sha256` | Khóa nội dung để phát hiện file bị đổi hoặc trùng |
| `document_type` | Ví dụ: biên bản hiện trường, báo giá sửa chữa, hóa đơn |
| `reference_text_path` | Transcript chuẩn đã được duyệt, lưu riêng cạnh ảnh |
| `annotation_status` | Phải là `adjudicated` |
| `consent_or_legal_basis` | Mã consent/quyền sử dụng, không ghi PII vào Git |
| `pii_treatment` | `synthetic`, `redacted` hoặc `controlled_private` |
| `benchmark_tier` | `domain_validation` cho dữ liệu thật đã duyệt; `synthetic_engineering` cho bộ tổng hợp |
| `reference_fields` | Trường nghiệp vụ đã xác minh như `total_vnd`, `document_date`, `plate_number`; không bắt buộc ở v1 |

Ví dụ cấu trúc private:

```text
vietnamese_ocr_validation_v1/
├── manifest.jsonl
├── images/
│   └── VN-OCR-0001.png
└── transcripts/
    └── VN-OCR-0001.txt
```

Ví dụ một dòng manifest:

```json
{"sample_id":"VN-OCR-0001","split":"validation","image_path":"images/VN-OCR-0001.png","image_sha256":"<64 hex>","document_type":"repair_estimate","reference_text_path":"transcripts/VN-OCR-0001.txt","annotation_status":"adjudicated","consent_or_legal_basis":"CONSENT-BATCH-01","pii_treatment":"redacted","benchmark_tier":"domain_validation"}
```

Prediction JSONL chỉ cần:

```json
{"sample_id":"VN-OCR-0001","predicted_text":"...","latency_seconds":12.4,"model_version":"ppocr-vietnamese-candidate-v1"}
```

## Quy tắc tạo nhãn chuẩn

1. Người gán nhãn thứ nhất chép đúng ký tự nhìn thấy, gồm dấu tiếng Việt, chữ số và dấu câu.
2. Người thứ hai kiểm tra độc lập trên ảnh gốc.
3. Reviewer xử lý điểm bất đồng và chuyển trạng thái thành `adjudicated`.
4. Unicode được chuẩn hóa NFC; khoảng trắng trong dòng được gom; không tự sửa chính tả.
5. Ảnh và transcript thô ở kho private/DVC. Git chỉ chứa code, schema và báo cáo tổng hợp không có nội dung PII.
6. Một SHA-256 chỉ xuất hiện một lần trong validation để tránh làm đẹp metric bằng ảnh trùng.

## Chạy OCR candidate có resume

Prediction và transcript đều chứa dữ liệu nhạy cảm nên đặt trong kho private, không đặt dưới Git repository. Runner ghi xong từng trang; nếu Colab/máy local dừng giữa chừng, chạy lại với `--resume` để tiếp tục đúng cấu hình và manifest cũ.

```powershell
.\.venv\Scripts\python.exe scripts\run_vietnamese_ocr_candidate.py `
  --manifest D:\private_data\vietnamese_ocr_validation_v1\manifest.jsonl `
  --output D:\private_data\vietnamese_ocr_validation_v1\predictions_robust.jsonl `
  --lang vi `
  --profile robust `
  --resume
```

Mỗi run có file sidecar `.run.json` khóa SHA-256 manifest và cấu hình. Runner từ chối resume nếu ngôn ngữ, profile, resize hoặc manifest đã đổi.

## Tính metric tổng hợp

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_vietnamese_ocr.py `
  --manifest D:\private_data\vietnamese_ocr_validation_v1\manifest.jsonl `
  --predictions D:\private_data\vietnamese_ocr_validation_v1\predictions_robust.jsonl `
  --output reports\metrics\documents\vietnamese_ocr_validation_v1.json `
  --minimum-pages 50
```

Runner khóa manifest/prediction bằng SHA-256 và xuất:

- CER, WER và exact match toàn tập;
- tỷ lệ hiện diện chính xác theo từng trường nghiệp vụ để đo khả năng giảm nhập tay;
- metric theo loại chứng từ;
- latency mean, median và p95;
- số trang OCR trả rỗng;
- số trang chỉ sai dấu tiếng Việt;
- 10 trang có CER cao nhất để làm error analysis;
- gate số trang tối thiểu.

Report không chứa transcript thật hoặc output OCR thô.

## Cách chọn candidate

Mỗi cấu hình như `robust`, deskew, crop hoặc model tiếng Việt phải sinh prediction file riêng trên cùng manifest. Chỉ chọn candidate khi:

1. CER/WER hoặc field accuracy tốt hơn baseline trên validation đã khóa;
2. không làm giảm chất lượng nghiêm trọng ở bất kỳ loại chứng từ chính nào;
3. latency p95 có thể chấp nhận cho quy trình duyệt;
4. correction rate/thời gian duyệt được đo trong UAT;
5. checkpoint, dependency, cấu hình và hash prediction được lưu;
6. không xem final test trong lúc chọn cấu hình.

Gate này được thực thi bằng `scripts/compare_vietnamese_ocr_candidates.py`: candidate chỉ được chọn khi chạy cùng tier/cùng số trang, CER và mean latency đều tốt hơn, đồng thời mọi field nghiệp vụ không giảm. Nếu thiếu field ground truth thì candidate vẫn ở trạng thái thử nghiệm.

Gate 50 trang chỉ cho phép công bố metric đúng miền ở mức nghiên cứu. Nó không tự động chứng minh production readiness.

Bộ tổng hợp có thể dùng `benchmark_tier=synthetic_engineering` và `annotation_status=source_verified` khi transcript lấy từ nguồn sinh tài liệu. Gate của tier này chỉ cho phép so sánh kỹ thuật giữa candidate; dù đủ số trang, report vẫn khóa `enough_pages_for_domain_claim=false`.
