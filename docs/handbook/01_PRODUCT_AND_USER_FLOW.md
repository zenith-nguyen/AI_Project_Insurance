# 01 — Sản phẩm và luồng người dùng

## Sản phẩm

Claim Review Workbench là bàn làm việc chung cho người duyệt claim. Một `claim_id` liên kết dữ liệu hồ sơ, ảnh xe, chứng từ, thực thể liên quan, kết quả model và quyết định của reviewer.

## Luồng chuẩn

```text
Tạo claim
→ tải ảnh/chứng từ
→ hệ thống tự phân tích các module khả dụng
→ reviewer xem risk/evidence/cảnh báo
→ reviewer sửa OCR/KIE nếu cần
→ reviewer lưu quyết định và lý do
```

Authenticity chạy tự động khi upload ảnh. Guided capture giúp yêu cầu ba góc chụp theo một phiên 10 phút; mức bảo đảm hiện là `guided_unverified`, chưa phải chứng thực camera phần cứng.

## Khi thiếu dữ liệu

- Thiếu ảnh, chứng từ hoặc graph: hệ thống vẫn có thể trả risk score nếu đủ feature bảng; kết quả là `partial`.
- Thiếu feature bắt buộc của XGBoost: kết quả là `blocked`, không có risk score.
- Không có graph không được diễn giải thành “không có quan hệ”.
- Không có marker AI/C2PA không chứng minh ảnh là ảnh camera thật.

## Quyết định con người

Reviewer chọn tiếp tục xử lý, yêu cầu bổ sung bằng chứng hoặc chuyển rà soát chuyên sâu. Điểm model là điểm xếp hạng nghiên cứu, không phải xác suất gian lận đã hiệu chuẩn cho production.

