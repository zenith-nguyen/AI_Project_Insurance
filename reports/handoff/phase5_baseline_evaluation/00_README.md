# Phase 5 — Baseline & Evaluation handoff kit

**Ngày cập nhật:** 19/10/2026
**Người nhận:** thành viên phụ trách Baseline B0–B5 và Evaluation Report

## Đọc theo thứ tự

1. `01_TASK_BRIEF_AND_B0_B5.md` — phạm vi, định nghĩa B0–B5 và điều được phép kết luận.
2. `02_EXPERIMENT_PROTOCOL.md` — split, leakage gate, metric, paired bootstrap và biểu đồ.
3. `03_DATA_AND_PREDICTION_CONTRACT.md` — dữ liệu/format cần giao giữa người train và người evaluation.
4. `04_RUNBOOK.md` — lệnh chạy và output cần nộp.
5. `05_REPORT_TEMPLATE.md` — khung Baseline & Evaluation Report.
6. `06_REVIEW_CHECKLIST.md` — checklist review/Definition of Done.
7. `phase5_predictions_SCHEMA_EXAMPLE.csv` — file giả chỉ để kiểm tra format, tuyệt đối không dùng làm kết quả.
8. `07_REFERENCE_MAP.md` — bản đồ file evidence hiện có trong repo.

## Code đã chuẩn bị

- Cấu hình: `configs/phase5_evaluation.v1.yaml`
- Evaluator: `scripts/evaluate_phase5_baselines.py`
- Paired CI: `src/evaluation/metrics.py::paired_stratified_bootstrap`

## Điều quan trọng nhất

Hiện có thể phát triển B0–B2 bằng dữ liệu tabular `train_fs/val_fs`. B3–B5 chỉ được tính PR-AUC/Recall@K khi ảnh, chứng từ, quan hệ và nhãn thuộc **cùng claim_id**, đồng thời mọi dữ liệu đầu vào đã tồn tại trước `scored_at`.

Không ghép hàng Kaggle, ảnh CarDD và hóa đơn SROIE thành một “claim” giả để công bố metric B3–B5.
