# 04 — Model, chỉ số và giới hạn

| Module | Vai trò | Evidence hiện tại | Trạng thái |
|---|---|---:|---|
| XGBoost | Xếp hạng claim | AP 0,559; Recall@10% 22,4% trên frozen test | Research validated |
| YOLOv8s-seg | Phân vùng hư hỏng | mask mAP50-95 0,5140 | Final test complete |
| DiT | Phân loại chứng từ | macro-F1 0,9283 | Research validated |
| PaddleOCR | Đọc chữ/vị trí | CER 0,4097; WER 0,5592 | Cần cải thiện |
| LayoutLMv3 | Trích xuất date/total | final-test field micro-F1 0,8659 | Final test complete |
| Rules v2 | Đối chiếu claim/chứng từ; fallback khi field sai/thiếu/low-confidence | Engineering tests + binary golden run | Chờ rule-owner sign-off |
| NetworkX v2 | Quan hệ point-in-time; chuẩn hóa phone/plate/shop | Engineering tests + binary golden run | Chờ case đã xác minh |
| Media authenticity | Provenance/reuse/forensics | Contract tests | Cần benchmark miền thật |

KPI Recall@10% tuyệt đối 60% không khả thi trên dataset có prevalence 24,7% vì hàng chờ 10% chỉ chứa tối đa khoảng 40,5% tổng positive. Mục tiêu phù hợp là uplift so với baseline, precision trong queue, calibration và Net Value với chi phí thật.

Không tối ưu tiếp theo final test đã khóa. Cải thiện bằng validation, dữ liệu mới, error analysis và domain validation.

## Model nào do nhóm huấn luyện?

- **XGBoost** được nhóm huấn luyện trên dữ liệu bảng Layer B, với preprocessing fit trong fold/split huấn luyện. Artifact dùng để chấm live là `bundle.joblib` và được kiểm tra SHA-256.
- **YOLOv8s-seg** được fine-tune trên CarDD để phân vùng hư hỏng; checkpoint được chọn bằng validation rồi mở final test đúng một lần.
- **LayoutLMv3** được fine-tune để trích xuất `date` và `total`; checkpoint 264 được chọn trên validation và final test đã khóa.
- **DiT** và **PaddleOCR** là model pretrained chạy cục bộ. Nhóm đã đánh giá độc lập DiT và benchmark OCR; không tuyên bố đã huấn luyện hai model này từ đầu.
- **Rules** và **NetworkX** là thuật toán xác định, không phải LLM.
- **Media authenticity** hiện là pipeline provenance, metadata, dấu phần mềm chỉnh sửa, exact/near-duplicate và kiểm tra reuse giữa claim. Pixel forensic adapter chỉ được bật khi có checkpoint đã hiệu chuẩn trên benchmark ảnh bảo hiểm.

Không có model LLM bên ngoài trong luồng phân tích claim. “Chạy local” có thể kiểm chứng qua model registry, hash artifact, `/readiness`, `/system/model-evidence` và log test. Việc không tìm thấy C2PA/SynthID/metadata không chứng minh ảnh thật; detector AI phổ quát chưa có đủ bằng chứng để dùng làm kết luận nghiệp vụ.

Kế hoạch nâng cấp có technical gate và business KPI cho từng module nằm tại `reports/MODEL_IMPROVEMENT_ROADMAP_2026-10-15.md`; trạng thái có bằng chứng mới nhất nằm tại `reports/MODEL_IMPROVEMENT_STATUS_2026-10-15.md`.

