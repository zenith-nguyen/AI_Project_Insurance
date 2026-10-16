# Nâng cấp ảnh, chứng từ và UI — 2026-10-16

## Kết quả đã đưa vào sản phẩm

| Năng lực | Kết quả kỹ thuật | Giá trị nghiệp vụ | Giới hạn phải nói rõ |
|---|---|---|---|
| Đọc biển số từ ảnh xe | PaddleOCR local + chuẩn hóa mẫu biển Việt Nam; cache theo file; vẽ khung đỏ trên ảnh | Đối chiếu biển số nhìn thấy với hồ sơ khai báo, giảm thao tác nhập lại | Ảnh xa, mờ, lóa hoặc che biển có thể không đọc được; hệ thống không đoán |
| Khoanh vùng hư hỏng | YOLOv8s-seg local trả box, mask, lớp và confidence | Giúp giám định viên nhìn nhanh vị trí model nghi ngờ hư hỏng | Là gợi ý trên ảnh; không tự xác nhận nguyên nhân, chi phí hoặc trách nhiệm |
| Chứng từ | DiT → PaddleOCR → LayoutLMv3/rule fallback chạy local | Đọc loại chứng từ, ngày, tổng tiền và biển số để người duyệt đối chiếu | OCR toàn văn còn yếu trên chứng từ Việt Nam thực; cần validation 50–100 trang có quyền sử dụng |
| Nguồn gốc ảnh | Sáu lớp: metadata, khai báo AI/chỉnh sửa, C2PA, reuse, pixel model đã hiệu chuẩn, SynthID | Chỉ ra căn cứ cụ thể và hành động tiếp theo thay vì gắn nhãn “ảnh giả” chung chung | Không có universal detector; ảnh bị xóa metadata, chụp lại màn hình hoặc dùng generator mới vẫn có thể lọt |
| Quan hệ | NetworkX point-in-time dùng điện thoại, xưởng, biển số và liên kết lịch sử | Mở hồ sơ liên quan để kiểm tra tái sử dụng thông tin hoặc quan hệ hợp lệ | Liên kết là đầu mối điều tra, không phải bằng chứng gian lận |
| Audit | Quyết định, chỉnh sửa và lý do được lưu theo claim | Có lịch sử truy vết ai làm gì và khi nào | Quyết định cuối cùng vẫn thuộc người duyệt |

## Cách đọc authenticity trên UI

UI hiển thị `x/6 lớp kiểm tra đã chạy`. Con số này chỉ là **độ phủ kỹ thuật**. Nó không phải xác suất ảnh thật và không phải điểm gian lận.

- Cờ đỏ: có căn cứ cụ thể cần xử lý, ví dụ metadata khai báo AI hoặc ảnh được dùng lại.
- Màu vàng: lớp kiểm tra chưa sẵn sàng hoặc kết quả chưa đủ kết luận.
- Màu xanh: lớp đã chạy và chưa thấy dấu vết trong phạm vi lớp đó.
- `Chưa đủ căn cứ`: hệ thống không có bằng chứng đủ mạnh để nói ảnh camera gốc hay ảnh AI.

Google cũng mô tả SynthID theo phạm vi nhà cung cấp: phát hiện được watermark cho biết nội dung do Google AI tạo/chỉnh sửa; không thấy watermark không loại trừ nội dung từ công cụ AI khác. Vì vậy sản phẩm giữ trạng thái bất định và có thể yêu cầu phiên chụp mới có hướng dẫn. Nguồn: [Gemini Apps Help — Verify Google AI-generated images and videos](https://support.google.com/gemini/answer/16722517?hl=en-CU).

## Smoke test bộ demo v3

Claim: `CLM-DEMO-V3-SMOKE-20261016`.

- OCR ảnh đọc `51K-482.76`, confidence `0,99997699`.
- YOLO trả 6 dự đoán vùng hư hỏng.
- Authenticity chạy 3/6 lớp; phát hiện metadata AI và ảnh gần trùng.
- Document pipeline phân loại `form` với confidence `0,8885`.
- Chứng từ trích đúng ngày `2026-10-12`, tổng tiền `42.680.000 VNĐ` và biển số `51K-482.76` bằng rule fallback trên OCR.
- XGBoost bị khóa trong smoke do script không cấp 29 feature bảng. Trên UI, bật **Dùng hồ sơ mẫu** để backend cấp feature demo; người dùng nghiệp vụ không nhập JSON.

Kết quả này chứng minh luồng chạy đầu cuối trên dữ liệu tổng hợp. Nó không chứng minh độ chính xác trên claim bảo hiểm Việt Nam thật.

## Bộ dữ liệu trình diễn

Thư mục: `D:\My Dowload\00_DEMO_HO_SO_BAO_HIEM_VIET_2026-10-16_v3`.

Mỗi case có ảnh xe, chứng từ PNG, bản PDF, thông tin cần nhập, hướng dẫn chạy và JSON tham chiếu dành cho dev/QA. Người dùng chỉ tải ảnh/chứng từ và nhập các trường trên form; không upload JSON.

Cấu trúc chứng từ tổng hợp tham khảo các nhóm tài liệu thường có trong hồ sơ xe cơ giới như thông báo tai nạn/yêu cầu bồi thường, giấy chứng nhận bảo hiểm, đăng ký xe, giấy phép lái xe và hồ sơ giám định; bộ demo không sao chép thương hiệu hay biểu mẫu của doanh nghiệp thật. Nguồn tham khảo: [Cẩm nang bảo hiểm phi nhân thọ — Bảo Việt](https://www.baoviet.com.vn/insurance/Uploads/Library/Document/hiep-hoi-bao-hiem-cam-nang-bao-hiem-phi-nhan-tho.pdf), [Quy tắc bảo hiểm xe ô tô — PJICO](https://www.pjico.com.vn/wp-content/uploads/2016/06/Quy-t%E1%BA%AFc-k%E1%BA%BFt-h%E1%BB%A3p-xe-%C3%B4-t%C3%B4-PJICO.pdf).

## Definition of Done còn lại

1. 50–100 trang chứng từ Việt Nam thật có quyền sử dụng, che PII, hai người gán nhãn và adjudication.
2. Bộ ảnh camera thật, ảnh chỉnh sửa, social re-encode, screen recapture và ảnh AI có nhãn nguồn gốc để benchmark authenticity.
3. Ảnh xe đúng miền bảo hiểm Việt Nam có mask hư hỏng và biển số đã che/được phép dùng để đánh giá YOLO/plate OCR.
4. Security/privacy review, latency/load test, backup/restore và quyền truy cập theo vai trò.
5. UAT có người nghiệp vụ ký xác nhận; monitoring, rollback và quy trình xử lý sai lệch.

Chỉ khi đủ các mục trên mới nên gọi hệ thống là pilot-ready. Bản hiện tại là research prototype có model local, checkpoint/version/hash, fallback và audit trail.
