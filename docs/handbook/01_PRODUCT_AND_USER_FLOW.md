# 01 — Sản phẩm và luồng người dùng

## Sản phẩm

Claim Review Workbench là bàn làm việc chung cho người duyệt claim. Một `claim_id` liên kết dữ liệu hồ sơ, ảnh xe, chứng từ, thực thể liên quan, kết quả model và quyết định của reviewer.

## Luồng chuẩn

```text
Tạo claim
→ tải ảnh/chứng từ
→ hệ thống tạo job nền và hiện giai đoạn/thời gian đang phân tích
→ hệ thống tự phân tích các module khả dụng
→ reviewer xem risk/evidence/cảnh báo
→ reviewer sửa OCR/KIE nếu cần
→ reviewer lưu quyết định và lý do
```

Authenticity chạy tự động khi upload ảnh. Guided capture dùng khi ảnh cũ, trùng hoặc nguồn gốc chưa rõ: hệ thống yêu cầu ba góc trong một phiên 10 phút và gắn session/step/hash để truy vết. Mức bảo đảm hiện là `guided_unverified`, chưa phải chứng thực camera phần cứng hoặc kết luận ảnh thật.

Job phân tích chạy phía máy chủ nên người dùng có thể mở Dashboard trong lúc chờ. Dashboard hiện trạng thái **Đang phân tích**; trang nạp hồ sơ hiện giai đoạn và số giây. Khi hồ sơ và bằng chứng không đổi, hệ thống dùng lại kết quả đã lưu. Tải thêm tệp sẽ tự làm kết quả cũ hết hiệu lực.

## Khi thiếu dữ liệu

- Thiếu ảnh, chứng từ hoặc graph: hệ thống vẫn có thể trả risk score nếu đủ feature bảng; kết quả là `partial`.
- Thiếu feature bắt buộc của XGBoost: kết quả là `blocked`, không có risk score.
- Không có graph không được diễn giải thành “không có quan hệ”.
- Không có marker AI/C2PA không chứng minh ảnh là ảnh camera thật.

## Quyết định con người

Reviewer chọn tiếp tục xử lý, yêu cầu bổ sung bằng chứng hoặc chuyển rà soát chuyên sâu. Điểm model là điểm xếp hạng nghiên cứu, không phải xác suất gian lận đã hiệu chuẩn cho production.

Tab **Quan hệ** ưu tiên giải thích hồ sơ nào liên quan, loại thông tin dùng chung, vì sao cần quan tâm và việc nên làm. Các chỉ số NetworkX nằm trong phần kỹ thuật. Tab **Nhật ký** luôn cho biết lượt phân tích đang tham chiếu; sau khi người duyệt lưu quyết định hoặc sửa trường chứng từ, nó ghi người thực hiện, thời gian, nội dung và lý do.

## Một địa chỉ dùng khi demo

Chỉ mở `http://127.0.0.1:8000/`. Trang chủ là hàng đợi vận hành; menu trong ứng dụng chuyển sang nạp hồ sơ, workbench, bằng chứng, quan hệ và nhật ký. `/dashboard` và `/intake` vẫn được giữ làm alias kỹ thuật nhưng người demo không cần nhớ.

Ba chỉ số đầu trang có nghĩa riêng:

- **Điểm xếp hạng XGBoost**: vị trí ưu tiên nghiên cứu trên thang 0–100. Đây không phải xác suất gian lận.
- **Loại đầu vào đã nhận**: ví dụ `3/3 loại` nghĩa là đã nhận dữ liệu khai báo, ảnh và chứng từ. Nó không đo độ đúng hoặc chất lượng của nội dung.
- **Cờ cần kiểm tra**: tổng số phát hiện mà người duyệt phải mở xem; giao diện tách số cờ mức cao và số cờ cần rà soát.

`Ưu tiên cao` phải luôn đi cùng lý do cụ thể như ảnh bị dùng lại, thông tin không khớp hoặc điểm xếp hạng cao. Khi thiếu feature bảng, giao diện hiển thị `Chưa chấm` và vẫn cho phép xử lý các cờ ảnh/chứng từ đã có.

