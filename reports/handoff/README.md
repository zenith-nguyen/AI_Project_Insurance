# Gói handoff Báo cáo tiến độ 2

Các file dưới đây dùng số liệu đã chạy trong repo và kết quả CarDD được xác minh trên Colab đến ngày 06/10/2026. Người nhận có thể đọc và viết phần báo cáo của mình mà không cần chạy code.

| PIC | File nên nhận | Nội dung |
|---|---|---|
| Nhật Quyên | `data_dictionary.md` | 39 cột nguồn và 42 cột Silver |
| Nhật Quyên | `model_card.md` | Mục tiêu, dữ liệu, pipeline, metric và giới hạn |
| Nhật Quyên | `data_audit_report.md` | EDA, missing values và leakage |
| Anh Thư | `model_selection_matrix.md` | So sánh bốn model bằng CV |
| Anh Thư | `metrics_v1.md` | Metric frozen test để đưa vào báo cáo |
| Tú Anh | `cardd_summary.md` | Trạng thái CarDD và thông tin còn phải xác minh |
| Tú Anh | `risk_register_v2_additions.md` | Các rủi ro mới từ sau Risk Register v1 |
| Thanh Vy | `layer_c_scenario_script.py` | Sinh biến thể ảnh cho kịch bản 3, 4, 5 và 8 |
| Tất cả thành viên | `document_network_scope.md` | Quyết định phạm vi Document và Network |

Lưu ý: CarDD đã được inspect trên Colab. Hiện có 2.753 ảnh nhưng 2.816 sample record và license yêu cầu prior consent cho nghiên cứu; chưa chuyển đổi/train trước khi xử lý hai điểm này.
