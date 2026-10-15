# Báo cáo nâng cấp OCR/KIE và benchmark ba hồ sơ demo

Ngày khóa kết quả: 2026-10-15  
Phạm vi: ba hồ sơ tổng hợp v2 trên máy demo hiện tại  
Kết luận phát hành: **chấp nhận Hybrid KIE v2; từ chối cấu hình OCR resize 1024 làm mặc định**

## Điều đã được nâng cấp

Luồng chứng từ hiện kết hợp hai nguồn:

1. LayoutLMv3 dự đoán trường ngày và tổng tiền.
2. Quy tắc xác định đọc ngày ISO, biển số và các số tiền có đơn vị VND.
3. Nếu model không có trường hợp lệ, hệ thống dùng `rule_fallback`.
4. Nếu model và rule mâu thuẫn, hệ thống ghi `kie_model_rule_conflict:<field>`.
5. Nếu confidence của model thấp hơn ngưỡng khóa `0,75`, hệ thống chọn rule và ghi phương pháp `rule_override_low_confidence`.
6. UI hiển thị tên trường theo nghiệp vụ, nguồn tạo giá trị và cờ yêu cầu đối chiếu bản gốc.

Đây là nâng cấp tầng suy luận và kiểm soát chất lượng của model đang có. LayoutLMv3 không được train lại trong thay đổi này và final test đã khóa không bị sử dụng để tối ưu.

## Business gate

Một hồ sơ chỉ PASS khi đồng thời:

- nhận đủ ảnh xe và chứng từ;
- XGBoost, nguồn gốc ảnh, YOLO, document pipeline, consistency và graph đều hoàn tất;
- có trace ID và version model;
- ngày chứng từ, tổng tiền và biển số khớp expected value của hồ sơ tổng hợp;
- case quan hệ tìm được claim liên quan;
- case nguồn gốc ảnh tạo được tín hiệu yêu cầu rà soát.

PASS ở đây chứng minh luồng kỹ thuật trên ba hồ sơ tổng hợp. Nó không phải metric độ chính xác trên dữ liệu bảo hiểm Việt Nam thật.

## Kết quả candidate

| Candidate | Cấu hình | Business gate | Quyết định |
|---|---|---:|---|
| Runtime baseline | OCR robust; gate ban đầu chưa kiểm tra exact critical fields | 3/3 gate cũ | Chỉ dùng làm mốc latency |
| OCR nhanh | Bỏ orientation/unwarping/text-line orientation; resize cạnh dài 1024 | 1/3 gate mới | **Từ chối làm mặc định** |
| Hybrid KIE v2 | OCR robust; conflict threshold 0,75; rule fallback có audit | 3/3 gate mới | **Chấp nhận** |

Candidate OCR nhanh bị loại vì:

- case van đọc `14.442.000` thay vì `24.900.000`;
- case sedan đọc `21.315.000` thay vì `36.750.000`;
- tổng thời gian ba case là 344,9 giây, không chứng minh được cải thiện ổn định so với mốc trước.

Việc giữ profile thử nghiệm trong code giúp tiếp tục nghiên cứu, nhưng `scripts/run_live.ps1` mặc định dùng profile `robust` và không resize.

## Kết quả Hybrid KIE v2 được chấp nhận

| Hồ sơ | Ngày | Tổng tiền | Biển số | Gate | Thời gian |
|---|---|---:|---|---:|---:|
| Hatchback cam | 2026-10-09 | 31.600.000 | 59H24681 | PASS | 166,4 giây |
| Van trắng có quan hệ | 2026-10-10 | 24.900.000 | 50D61537 | PASS | 96,4 giây |
| Sedan xanh, nguồn gốc cần xem | 2026-10-11 | 36.750.000 | 61A90426 | PASS | 121,8 giây |

Lần chạy lại hồ sơ 01 không thay đổi mất `0,0` giây và trả `cache_hit=true`.

Thời gian 166,4 giây của hồ sơ đầu gồm cold start: nạp DiT, PaddleOCR, LayoutLMv3 và các processor. Không nên dùng riêng số này làm SLA xử lý warm.

## Nút thắt hiệu năng đã đo

Tổng thời gian vòng benchmark: 389,2 giây.

| Công đoạn | Tổng thời gian ba hồ sơ | Tỷ trọng xấp xỉ |
|---|---:|---:|
| PaddleOCR | 328,3 giây | 84,4% |
| Nạp document models | 23,6 giây | 6,1% |
| LayoutLMv3/KIE | 16,6 giây | 4,3% |
| YOLO | 7,3 giây | 1,9% |
| DiT | 6,0 giây | 1,5% |

Vì vậy bước tối ưu tiếp theo phải tập trung vào OCR. Không giảm chất lượng, bỏ module hoặc ép resize chỉ để làm số latency đẹp hơn.

## Giá trị nghiệp vụ

- Người duyệt thấy rõ `Tổng tiền`, `Ngày chứng từ`, `Biển số xe` thay cho tên schema kỹ thuật.
- Mỗi giá trị cho biết được lấy từ LayoutLMv3 hay rule dự phòng.
- Khi hai nguồn mâu thuẫn, hồ sơ có cờ đỏ/rà soát và giải thích lý do.
- Giá trị confidence thấp không còn âm thầm ghi đè con số rõ ràng có đơn vị tiền tệ.
- Mọi conflict đi vào warning và signal để audit, lọc hàng đợi và kiểm tra lại.

Hệ thống vẫn là công cụ hỗ trợ. Người duyệt phải nhìn vùng khoanh trên chứng từ gốc trước khi lưu quyết định.

## Việc tiếp theo

1. Tạo validation 50–100 trang chứng từ Việt Nam có ground truth và quyền sử dụng.
2. Đo field accuracy, correction rate và thời gian duyệt; không dùng ba hồ sơ demo làm accuracy benchmark.
3. Thử tiền xử lý/orientation/crop theo candidate riêng, chỉ phát hành nếu quality gate không giảm.
4. Thêm cache theo SHA-256 của từng evidence + model version để khi bổ sung một tệp, các tệp cũ không bị suy luận lại.
5. Preload model khi server khởi động và hiển thị trạng thái `đang làm nóng model` trên readiness/UI.
6. Sau khi có validation đúng miền, hiệu chỉnh ngưỡng conflict theo field thay vì dùng chung `0,75`.

## Bằng chứng tái lập

- Runner: `scripts/benchmark_demo_v2.py`
- Test gate: `tests/test_demo_v2_benchmark.py`
- Report máy: `reports/metrics/system/demo_v2_runtime_hybrid_2026-10-15.json`
- Candidate bị loại: `reports/metrics/system/demo_v2_runtime_optimized_rejected_2026-10-15.json`

