# Trạng thái dự án mới nhất — 2026-10-16

## Điều đã hoàn thành trong mốc này

| Hạng mục | Kết quả kỹ thuật | Ý nghĩa nghiệp vụ |
|---|---|---|
| Kiểm toán bộ 27 hồ sơ | 27/27 case, 9 scenario, 224 asset đúng hash; phát hiện 16 lỗi sửa được và 3 giới hạn point-in-time | Có bộ rehearsal rộng hơn để demo luồng và tìm lỗi dữ liệu trước khi dùng claim thật |
| Chuẩn hóa dữ liệu | 222 file đầu ra khóa hash; render lại 27 báo giá; tách expected khỏi input | Giảm rủi ro model nhìn đáp án và giúp thành viên khác chạy lại đúng bộ dữ liệu |
| OCR robust | CER 18,02%; WER 49,75%; 89,0 giây/trang; ngày/tiền/biển số 27/27 | Field chính hữu ích trên mẫu sạch, nhưng toàn văn và thời gian xử lý chưa đạt mức sản phẩm |
| OCR fast640 | CER 30,12%; 52,4 giây/trang; field chính 27/27 | Nhanh hơn 41,1% nhưng mất nhiều chữ; bị gate loại, không thay model live |
| Graph SC07-P | Tìm đúng 2/2 history trong scope riêng; không dùng dữ liệu tương lai | Đưa hồ sơ có nhiều thực thể dùng chung lên ưu tiên để người duyệt xác minh, không kết luận gian lận |
| Bộ gán nhãn thật | Labeling kit private có consent log, hai annotator và adjudication | Sẵn quy trình thu 50–100 trang hợp lệ để nâng OCR đúng miền |
| Kiểm thử code | 146 passed, 1 skipped trước smoke; test mới bao phủ tier lock, field metric, time rebase và graph scope | Giảm lỗi khi bàn giao cho thành viên khác trên Windows/local API |

## Trạng thái sản phẩm

Ứng dụng local vẫn chạy tại `http://127.0.0.1:8000/`. XGBoost, rules, NetworkX, media authenticity, YOLO và document pipeline được báo active qua `/readiness`. Hệ thống không gọi LLM ngoài để kết luận claim.

Bộ 27 hồ sơ **chưa phải bằng chứng accuracy trên bảo hiểm Việt Nam thật**. Hiện mới có 1/27 case được chạy actual theo graph-only smoke; OCR đã chạy đủ 27 báo giá nhưng các scenario còn lại vẫn cần chạy tách scope và được người nghiệp vụ ký UAT.

## Quyết định model

Giữ OCR `robust` trong cấu hình live. Không chuyển sang `fast640` vì promotion gate yêu cầu chất lượng và tốc độ cùng cải thiện. Cache theo hash vẫn được dùng để lần phân tích lại không lặp OCR của file không đổi.

## Việc tiếp theo

1. Thu thập 50–100 trang chứng từ Việt Nam có quyền sử dụng, che PII và adjudicate.
2. Chạy từng scenario còn lại trong bộ 27 theo scope riêng, ghi actual/expected và human sign-off.
3. Tìm OCR/runtime nhẹ hơn rồi đánh giá cùng CER, field accuracy, latency và correction time.
4. Đánh giá YOLO/authenticity trên dữ liệu đúng miền có nhãn; bộ 27 không có mask hư hỏng và ảnh camera thật đối chứng.
5. Chỉ nâng trạng thái research handoff khi golden end-to-end, handbook review và UAT đều PASS.
