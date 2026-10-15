# Benchmark OCR trên bộ 27 hồ sơ tổng hợp

Ngày chạy: 2026-10-16
Kết luận: **candidate nhanh bị loại bởi promotion gate; giữ `robust` làm cấu hình live hiện tại**

## Phạm vi và cách đọc

Benchmark dùng 27 báo giá được render lại từ PDF của bộ demo. Transcript lấy từ text layer nguồn và ba field nghiệp vụ gồm ngày chứng từ, tổng tiền, biển số. Toàn bộ dữ liệu là tổng hợp nên kết quả chỉ có giá trị so sánh kỹ thuật; `enough_pages_for_domain_claim=false`.

| Candidate | CER ↓ | WER ↓ | Mean latency ↓ | P95 latency ↓ | Ngày | Tổng tiền | Biển số |
|---|---:|---:|---:|---:|---:|---:|---:|
| `vi-robust` | 18,02% | 49,75% | 89,0 giây | 97,4 giây | 27/27 | 27/27 | 27/27 |
| `vi-fast_upright-max640` | 30,12% | 68,40% | 52,4 giây | 56,6 giây | 27/27 | 27/27 | 27/27 |

Candidate 640 giảm mean latency 36,6 giây/trang, tương đương khoảng 41,1%. Đổi lại, CER tăng 12,10 điểm phần trăm và WER tăng 18,65 điểm phần trăm. Ba field chính vẫn được tìm thấy trong bố cục sạch này, nhưng phần toàn văn kém hơn rõ rệt; điều đó có thể làm giảm chất lượng LayoutLMv3 trên chứng từ khó hơn.

## Quyết định

Promotion gate yêu cầu cùng tier, cùng số trang, candidate PASS, có business field ground truth, không giảm field accuracy, CER tốt hơn và mean latency tốt hơn. Candidate 640 đạt 6/7 kiểm tra nhưng thất bại ở `cer_improved`, nên trạng thái là **experimental/rejected**, không thay cấu hình live.

Candidate `max1280` được dừng sau một trang vì mất 77,7 giây, cải thiện quá ít so với baseline để đáng chạy thêm toàn bộ tập. Kết quả dở dang không được dùng làm metric hay chọn model.

## Ý nghĩa nghiệp vụ

- Trên mẫu tổng hợp sạch, cả hai cấu hình đều có thể hỗ trợ điền ngày, tiền và biển số.
- Full-text CER/WER còn cao, nên người duyệt vẫn phải xem chứng từ gốc và xác nhận trường được trích.
- Lần chạy đầu trên CPU còn quá chậm. Cache theo hash giúp lần chạy lại gần như không lặp OCR, nhưng không giải quyết latency của file mới.
- Chưa có cơ sở công bố độ chính xác trên chứng từ bảo hiểm Việt Nam thật.

## Mốc nâng cấp kế tiếp

1. Thu thập và adjudicate 50–100 trang bằng labeling kit private.
2. Đo field accuracy của OCR + LayoutLMv3 cùng nhau, không chọn OCR chỉ bằng CER.
3. So sánh model OCR nhẹ hơn hoặc runtime GPU/ONNX trên cùng manifest.
4. Thử crop theo vùng field và xử lý bất đồng bộ để UI trả trạng thái sớm; vẫn giữ bản gốc cho người duyệt.
5. Chỉ đổi cấu hình live khi candidate qua toàn bộ promotion gate và UAT giảm thời gian chỉnh sửa thực tế.

Aggregate evidence nằm tại:

- `reports/metrics/system/demo27_ocr_robust_2026-10-16.json`
- `reports/metrics/system/demo27_ocr_fast640_2026-10-16.json`
- `reports/metrics/system/demo27_ocr_comparison_2026-10-16.json`
