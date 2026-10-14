# Live multimodal UI verification — 2026-10-14

## Kết quả người dùng nhìn thấy

Claim `CLM-20261014-142539-923` đã được chạy bằng các checkpoint thật trên API local.

| Phần | Kết quả live | Ý nghĩa khi duyệt hồ sơ |
|---|---|---|
| Xếp hạng bảng | Điểm nghiên cứu `0.758947`; ưu tiên cao | Đưa hồ sơ lên trước trong hàng chờ; không phải xác suất gian lận |
| Ảnh hư hỏng | 5 vùng: 2 móp, 1 trầy xước, 1 đèn vỡ, 1 nứt | UI vẽ mask/box, tên lớp và confidence ngay trên ảnh |
| Chứng từ | DiT nhận dạng `questionnaire` với confidence khoảng 80%; PaddleOCR đọc 80 vùng chữ | UI vẽ khung OCR và cho xem trích đoạn đã đọc |
| KIE | Không trích được `date/total` | Biên bản tiếng Việt nằm ngoài miền SROIE tiếng Anh; người duyệt nhập giá trị đã đối chiếu và lưu audit log |
| Nguồn gốc ảnh | Trùng byte với ảnh trong 2 claim khác | Dấu hiệu tái sử dụng bằng chứng; cần mở hồ sơ liên quan, chưa phải kết luận gian lận |
| Quan hệ | Không có feed entity/edge cho claim này | Risk score vẫn có; UI ghi rõ phần quan hệ chưa được kiểm tra |

## Thay đổi đã xác minh

- Checkpoint YOLO được kiểm tra SHA-256 trước khi nạp.
- Checkpoint LayoutLMv3 được kiểm tra tree SHA-256 trước khi nạp.
- Ảnh xe hiển thị mask/box theo màu, nhãn tiếng Việt và confidence.
- Chứng từ hiển thị các vùng OCR màu xanh; trường KIE có cấu trúc dùng màu cam khi có.
- UI hiển thị kích thước, dung lượng và tiền tố SHA-256 của tệp.
- Khi KIE không tìm thấy trường, UI giải thích giới hạn miền dữ liệu và đưa ra hành động cụ thể.
- Chỉnh sửa của người duyệt ghi `original_value`, `corrected_value`, lý do, người thực hiện và trace vào audit log.
- Kết quả phân tích mới nhất được lưu trong thư mục runtime của claim. Tải lại trang hoặc khởi động lại API không phải chạy OCR lại; tải thêm bằng chứng sẽ tự vô hiệu hóa cache cũ.
- PaddleOCR trên Windows CPU tắt MKLDNN để tránh lỗi oneDNN/PIR; script setup pin PaddlePaddle dưới 3.3.

## Cách demo

1. Chạy `powershell -ExecutionPolicy Bypass -File scripts/run_live.ps1`.
2. Mở `http://127.0.0.1:8000/?claim_id=CLM-20261014-142539-923&tab=evidence`.
3. Chỉ vào các vùng màu trên ảnh xe để giải thích model đề nghị kiểm tra vị trí nào.
4. Chỉ vào khung xanh trên chứng từ để giải thích vùng PaddleOCR đã đọc.
5. Cho xem phần `Trường có cấu trúc`: model chưa lấy được ngày/tổng tiền trên mẫu tiếng Việt và không tự bịa giá trị.
6. Nhập một giá trị đã đối chiếu, ghi lý do ít nhất ba từ, bấm **Lưu chỉnh sửa vào nhật ký**, rồi mở tab **Nhật ký**.
7. Nhấn **Phân tích lại** chỉ khi muốn chạy lại toàn bộ model. Tải lại trang dùng kết quả đã lưu.

## Giới hạn phải nói rõ khi báo cáo

- Các lớp `crack`, `dent`, `scratch` của CarDD còn yếu trên final test; vùng khoanh là gợi ý rà soát.
- DiT được đánh giá trên RVL-CDIP, còn KIE được huấn luyện/evaluate trên SROIE; chưa phải validation chứng từ bảo hiểm Việt Nam.
- Không có marker provenance không chứng minh ảnh thật. Module hiện kiểm tra metadata, Content Credentials khi công cụ có sẵn và tái sử dụng ảnh giữa claim; pixel AI detector đúng miền vẫn chưa có benchmark.
- Thiếu chứng từ hoặc graph không chặn XGBoost tạo điểm xếp hạng nếu feature bảng đầy đủ. UI phải giữ trạng thái `partial` và nói rõ module chưa chạy.
