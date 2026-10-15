# Kiểm chứng preload model và cache theo từng evidence

Ngày kiểm chứng: 2026-10-16  
Phạm vi: runtime local, hồ sơ tổng hợp, model version hiện tại  
Kết luận: **PASS**

## Vấn đề được xử lý

Trước thay đổi này, hệ thống có cache cho toàn bộ claim. Khi người dùng tải thêm một ảnh hoặc chứng từ, kết quả claim cũ bị vô hiệu đúng cách nhưng toàn bộ ảnh và chứng từ cũ cũng bị suy luận lại. PaddleOCR là công đoạn chậm nhất nên thao tác bổ sung một tệp có thể khiến người dùng chờ lại hơn một phút.

## Thay đổi kỹ thuật

### Cache từng evidence

Mỗi output YOLO hoặc document pipeline được lưu riêng tại:

```text
runtime/claims/{claim_id}/inference_cache/
```

Khóa cache chứa:

- SHA-256 của evidence;
- loại module;
- version model/pipeline;
- hash artifact;
- cấu hình OCR gồm ngôn ngữ, profile và kích thước resize.

Cache chỉ được dùng khi cả tệp và version suy luận không đổi. `force_recompute=true` luôn bỏ qua cache và chạy lại model. File cache được ghi qua tệp tạm rồi replace để tránh đọc bản ghi dở dang.

### Preload model chứng từ

Khi chạy `scripts/run_live.ps1`, server khởi động một background warm-up cho DiT, PaddleOCR và LayoutLMv3. API vẫn trả lời trong lúc nạp model. `/readiness` công bố một trong các trạng thái:

- `scheduled`: đã lên lịch;
- `warming`: đang nạp model;
- `ready`: sẵn sàng;
- `error`: nạp thất bại và có lý do.

UI Intake và Dashboard diễn giải các trạng thái này bằng ngôn ngữ nghiệp vụ. Người demo biết hệ thống đang nạp model, thay vì nhìn màn hình chờ mà không rõ nguyên nhân.

## Benchmark tăng dần

Kịch bản:

1. Tạo claim với một ảnh xe và một chứng từ.
2. Chạy phân tích đầy đủ để tạo cache.
3. Tải thêm một ảnh xe khác.
4. Phân tích lại claim.

| Lần chạy | Công việc thực hiện | Thời gian |
|---|---|---:|
| Ban đầu | 1 ảnh + 1 chứng từ, chạy đầy đủ | 145,6 giây |
| Sau khi thêm ảnh | Dùng lại ảnh cũ và chứng từ cũ; YOLO chỉ chạy ảnh mới | 2,5 giây |

Mức giảm thời gian quan sát được là khoảng **98,3%** cho kịch bản bổ sung một ảnh. Đây là runtime benchmark trên máy hiện tại, không phải SLA production.

### Các gate đã PASS

- Chứng từ không đổi có `evidence_cache_hits = 1`.
- Ảnh cũ có `evidence_cache_hits = 1`.
- Hai ảnh được tổng hợp đầy đủ trong analysis.
- Lần phân tích tăng dần không có stage `document_ocr`.
- Lần phân tích tăng dần không có stage `document_kie`.
- `force_recompute` được unit test để xác nhận luôn gọi lại model.

## Giá trị nghiệp vụ

- Người dùng bổ sung ảnh không phải chờ đọc lại chứng từ cũ.
- Kết quả vẫn truy vết được vì cache phụ thuộc hash tệp và version model.
- Khi model hoặc cấu hình OCR thay đổi, cache cũ tự mất hiệu lực.
- Workbench ghi rõ số tệp đã dùng lại, tránh hiểu nhầm rằng module không chạy.
- Đội kỹ thuật vẫn có nút phân tích lại cưỡng bức để điều tra lỗi.

## Giới hạn

- Cache đang lưu trên filesystem local, phù hợp research/demo; pilot cần object storage/database, retention và concurrency policy.
- Cache chỉ tái sử dụng trong cùng evidence ID. Hai evidence ID khác nhau có nội dung giống nhau chưa dùng chung output model.
- Preload chuyển thời gian nạp model sang lúc mở server; nó không làm PaddleOCR nhận dạng nhanh hơn.
- OCR của lần chạy đầy đủ vẫn là nút thắt và cần validation chứng từ Việt Nam trước khi thay đổi preprocessing hoặc model.

## Bằng chứng

- Benchmark runner: `scripts/benchmark_incremental_cache.py`
- Kết quả máy: `reports/metrics/system/incremental_evidence_cache_2026-10-16.json`
- Cache store: `src/api/storage.py`
- Orchestration: `src/api/live.py`
- Warm-up state: `src/document/runtime.py`
- Test cache và force recompute: `tests/test_live_claim_service.py`

