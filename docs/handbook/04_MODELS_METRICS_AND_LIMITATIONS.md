# 04 — Model, chỉ số và giới hạn

| Module | Vai trò | Evidence hiện tại | Trạng thái |
|---|---|---:|---|
| XGBoost | Xếp hạng claim | AP 0,559; Recall@10% 22,4% trên frozen test | Research validated |
| YOLOv8s-seg | Phân vùng hư hỏng | mask mAP50-95 0,5140 | Final test complete |
| DiT | Phân loại chứng từ | macro-F1 0,9283 | Research validated |
| PaddleOCR | Đọc chữ/vị trí | CER 0,4097; WER 0,5592 | Cần cải thiện |
| LayoutLMv3 | Trích xuất date/total | final-test field micro-F1 0,8659 | Final test complete |
| Rules | Đối chiếu claim/chứng từ | Engineering demo | Demo only |
| NetworkX | Quan hệ point-in-time | Engineering demo | Demo only |
| Media authenticity | Provenance/reuse/forensics | Contract tests | Cần benchmark miền thật |

KPI Recall@10% tuyệt đối 60% không khả thi trên dataset có prevalence 24,7% vì hàng chờ 10% chỉ chứa tối đa khoảng 40,5% tổng positive. Mục tiêu phù hợp là uplift so với baseline, precision trong queue, calibration và Net Value với chi phí thật.

Không tối ưu tiếp theo final test đã khóa. Cải thiện bằng validation, dữ liệu mới, error analysis và domain validation.

