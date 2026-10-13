# LayoutLMv3 SROIE — Final test v1

**Ngày hoàn tất:** 13/10/2026
**Phạm vi:** trích xuất hai trường `date` và `total` từ SROIE processed v1.

## Kết quả

| Chỉ số | Validation chọn model | Final test |
|---|---:|---:|
| Field micro-F1 | 0,921409 | **0,865937** |
| Date F1 | — | **0,831956** |
| Total F1 | — | **0,899457** |
| Số ảnh | 93 | **361** |

Chênh lệch Field micro-F1 giữa validation và final test là `-0,055472`, tương đương khoảng 5,55 điểm phần trăm. Trường `total` tốt hơn trường `date` trên final test.

## Tính toàn vẹn protocol

- Candidate được chọn trên validation trước khi mở test.
- Checkpoint: `checkpoint-264`.
- Checkpoint tree SHA-256: `2b008c90f764c79be36f7082a96e84ba6d28aaccb512dd801123abe55c1ead3c`.
- Test gồm 361 ảnh và không được dùng để chọn epoch hoặc sửa alignment.
- Lần inference duy nhất hoàn tất 181/181 batch.
- Hàm tính metric ban đầu thiếu `metric_value`; metric được tính lại từ `EvalPrediction` còn trong RAM.
- Recovery không chạy inference lại và không đọc lại test.
- Final report và execution record đã được ghi với cùng `run_id`.

Artifact trên Google Drive:

```text
reports/metrics/documents/layoutlmv3_sroie_final_test_v1.json
reports/metrics/documents/layoutlmv3_sroie_final_test_v1.execution.json
```

## Cách diễn giải

Kết quả chứng minh pipeline KIE có khả năng trích xuất ngày và tổng tiền trên bộ receipt SROIE. Đây là validation nghiên cứu trên dữ liệu công khai, chưa phải bằng chứng hiệu quả trên chứng từ bảo hiểm Việt Nam. Không tiếp tục tối ưu checkpoint hoặc quy tắc theo 361 ảnh final test này.
