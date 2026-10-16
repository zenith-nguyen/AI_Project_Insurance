# Quyết định nâng cấp OCR live — 2026-10-16

## Quyết định

Live OCR được chuẩn hóa thành `lang=vi`, `profile=robust`, kích thước gốc. Đây là cấu hình có chất lượng tốt nhất trong benchmark 27 trang tổng hợp. Ba candidate nhanh đều giữ đúng ngày, tổng tiền và biển số 27/27 nhưng làm CER xấu đi, nên không được promote.

| Cấu hình | CER | WER | Mean latency | Trường nghiệp vụ | Quyết định |
|---|---:|---:|---:|---:|---|
| vi-robust, original | 18,02% | 49,75% | 89,0 giây | 27/27 mỗi trường | Giữ live |
| vi-fast, max640 | 30,12% | 68,40% | 52,4 giây | 27/27 mỗi trường | Reject |
| vi-fast, max1280 | 28,87% | 66,33% | 58,0 giây | 27/27 mỗi trường | Reject |
| vi-fast, max1600 | 27,96% | 63,05% | 68,3 giây | 27/27 mỗi trường | Reject |

## Ý nghĩa nghiệp vụ

Candidate nhanh giúp người dùng chờ ít hơn nhưng tạo thêm lỗi chữ. Điều này có thể làm tăng thời gian kiểm tra và sửa tay, nên chưa tạo ra lợi ích tổng thể. Cấu hình live ưu tiên chất lượng; cache theo SHA-256 và warm-up giải quyết phần lớn thời gian chờ khi mở lại hoặc phân tích lại cùng file.

Việc đặt rõ `INSURANCE_OCR_LANG=vi` khắc phục một lỗi cấu hình bàn giao: trước đây runtime mặc định có thể dùng `en` dù benchmark chọn tiếng Việt. Thành viên clone repo và chạy `scripts/run_live.ps1` bây giờ nhận đúng model ngôn ngữ đã đánh giá.

## Mốc nâng tiếp theo

1. Gán nhãn 50–100 trang chứng từ Việt Nam có quyền sử dụng và che PII.
2. Thử deskew, crop vùng nội dung và contrast theo điều kiện; không áp dụng cùng một biến đổi cho mọi trang.
3. Đánh giá runtime GPU/ONNX hoặc OCR nhẹ hơn trên cùng manifest.
4. Đo thêm correction time của người duyệt, không chọn model chỉ bằng CER.
5. Chỉ promote khi chất lượng trường nghiệp vụ không giảm, CER tốt hơn và latency/công sửa thực tế cùng cải thiện.

## Phạm vi kết luận

Bộ 27 trang là dữ liệu tổng hợp. Kết quả đủ để chọn cấu hình demo và kiểm tra pipeline, chưa đủ để tuyên bố accuracy trên chứng từ bảo hiểm Việt Nam thật.
