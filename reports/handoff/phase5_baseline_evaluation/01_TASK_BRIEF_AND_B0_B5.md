# 01 — Task brief và định nghĩa B0–B5

## Mục tiêu

Xây chuỗi ablation tăng dần từ rule đơn giản đến pipeline đầy đủ và trả lời ba câu hỏi:

1. Candidate có xếp hạng claim tốt hơn baseline không?
2. Module mới đóng góp thêm bao nhiêu trên **cùng claim/split**?
3. Mức tăng có đủ ổn định hay CI 95% của hiệu số vẫn chứa 0?

Hệ thống hỗ trợ ưu tiên hồ sơ cho con người. Score không phải xác suất gian lận production và không được dùng một mình để từ chối bồi thường.

## Định nghĩa khóa

| Stage | Thành phần | Input hợp lệ | Trạng thái dữ liệu hiện tại |
|---|---|---|---|
| B0 | Rule baseline | Dữ liệu bảng của claim | Chạy được |
| B1 | Logistic Regression | Cùng feature/split tabular với B0/B2 | Chạy được |
| B2 | XGBoost tabular | Dữ liệu bảng, chưa dùng ảnh/chứng từ/graph | Chạy được |
| B3 | B2 + document signals | OCR/KIE/classification của cùng claim, `received_at <= scored_at` | Chờ claim-linked labeled data |
| B4 | B3 + image signals | Damage/authenticity của ảnh cùng claim | Chờ claim-linked labeled data |
| B5 | B4 + consistency/relationship | Feature graph point-in-time, edge `available_at <= scored_at` | Chờ claim-linked labeled data |

Định nghĩa này phải được khóa trước khi mở external test. Nếu rubric chính thức của môn học có định nghĩa B0–B5 khác, cập nhật YAML và biên bản thay đổi trước khi chạy.

## Deliverables bắt buộc

- prediction CSV cho từng stage trên đúng cùng claim;
- bảng AP, Recall@5/10/20%, Precision@5/10/20%;
- bootstrap CI 95% riêng từng model và paired delta CI cho B1–B0, B2–B0, B2–B1, B5–B2;
- PR curves và Recall/Precision@K curves;
- error analysis ở top queue;
- model/data/split hash, seed và version;
- kết luận trung thực khi CI chứa 0;
- Baseline & Evaluation Report hoàn chỉnh.

## Phần nhóm đã có sẵn

- B0 rule implementation: `src/baselines/rules.py`.
- B1/B2 model factory và preprocessing: `src/models/train.py`.
- Metric/top-K/bootstrap: `src/evaluation/metrics.py`.
- Split phát triển mới: `data/gold/feature_selection_v1/{train_fs,val_fs}.parquet`.
- Baseline ownership: `configs/baseline_registry.v1.yaml`.

## Phần người nhận task phải làm

1. Xác nhận field nào có sẵn ở từng thời điểm chấm.
2. Tạo predictions B0–B2 trên `val_fs` mà không đọc test cũ để chọn feature/model.
3. Chuẩn bị data contract B3–B5 và đánh dấu blocked nếu chưa có claim-linked labels.
4. Chạy evaluator, đọc paired CI, viết error analysis và báo cáo.
5. Không biến engineering PASS của graph/OCR/YOLO thành PR-AUC của claim fraud.
