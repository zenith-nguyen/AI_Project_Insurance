# Gói handoff Báo cáo tiến độ 2

Các file dưới đây dùng số liệu đã chạy trong repo và kết quả CarDD được xác minh trên Colab đến ngày 10/10/2026. Người nhận có thể đọc và viết phần báo cáo của mình mà không cần chạy code.

| PIC | File nên nhận | Nội dung |
|---|---|---|
| Nhật Quyên | `data_dictionary.md` | 39 cột nguồn và 42 cột Silver |
| Nhật Quyên | `model_card.md` | Mục tiêu, dữ liệu, pipeline, metric và giới hạn |
| Nhật Quyên | `data_audit_report.md` | EDA, missing values và leakage |
| Anh Thư | `model_selection_matrix.md` | So sánh bốn model bằng CV |
| Anh Thư | `metrics_v1.md` | Metric frozen test để đưa vào báo cáo |
| Tú Anh | `cardd_summary.md` | CarDD baseline, candidate, model selection và final-test status |
| Tú Anh | `risk_register_v2_additions.md` | Các rủi ro mới từ sau Risk Register v1 |
| Thanh Vy | `layer_c_scenario_script.py` | Sinh biến thể ảnh cho kịch bản 3, 4, 5 và 8 |
| Tất cả thành viên | `document_network_scope.md` | Quyết định phạm vi Document và Network |
| Đội UI + ML/backend | `../API_HANDOFF_GUIDE_2026-10-13.md` | Luồng API, client dùng sẵn, guided capture, mã lỗi và phân công |

Lưu ý: CarDD đã được convert, validate và train trên Colab. YOLOv8s được chọn bằng validation; final test đã chạy đúng một lần trên 419 ảnh/931 instance, mask mAP50-95 `0,513978`, và artifact verification PASS. Không chạy lại hoặc tinh chỉnh theo final test. License vẫn yêu cầu prior consent cho nghiên cứu; nhóm cần lưu bằng chứng consent và không phân phối raw data.
