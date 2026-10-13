# Bộ hồ sơ mẫu để demo màn hình Nạp hồ sơ

Tất cả nội dung trong folder này là **dữ liệu giả lập**, chỉ dùng để trình diễn và kiểm thử.

## Cách chạy nhanh

1. Mở `http://127.0.0.1:8000/intake`.
2. Bấm **Điền toàn bộ dữ liệu mẫu**. Màn hình sẽ tự điền số tiền, ngày sự cố, biển số và Feature bảng JSON.
3. Ở **Ảnh xe**, chọn `03_ANH_XE_DEMO_AI.png`.
4. Ở **Chứng từ**, chọn `04_CHUNG_TU_DEMO_GIA_LAP.png`.
5. Bấm **1 · Lưu hồ sơ và tệp**.
6. Bỏ qua bước chụp có hướng dẫn; bấm **3 · Phân tích tự động**.
7. Bấm **4 · Xem kết quả**.

Nếu hệ thống báo Claim ID đã tồn tại, bấm **Tạo mã mới** rồi thực hiện lại bước 5.

## Feature bảng dạng JSON là gì?

Đó là các trường dữ liệu dạng bảng mà XGBoost cần để tính điểm rủi ro, ví dụ tuổi khách hàng, thời gian tham gia bảo hiểm, loại tai nạn, số tiền yêu cầu và thông tin xe. JSON là cách biểu diễn dữ liệu theo cặp:

```json
{
  "age": 37,
  "incident_type": "Multi-vehicle Collision",
  "total_claim_amount": 67140
}
```

File `02_FEATURE_BANG_DAY_DU.json` chứa đủ bộ trường mẫu. Trong sản phẩm thực tế, backend lấy các trường này từ hệ thống nghiệp vụ; người duyệt không phải nhập JSON thủ công.

## Lưu ý kết quả demo

- Ảnh xe được tạo bằng AI để thử luồng kiểm tra tính xác thực; hệ thống không được phép kết luận gian lận chỉ vì ảnh là AI hoặc thiếu metadata.
- Chứng từ là phiếu báo giá giả lập.
- Các module thiếu checkpoint sẽ được ghi là `unavailable` hoặc tạo cảnh báo; điểm tổng hợp vẫn có thể chạy ở trạng thái `partial` nếu XGBoost có đủ feature.
