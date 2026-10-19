# 04 — Runbook

## 1. Chuẩn bị môi trường

```powershell
cd D:\AI_Project_Insurance
.\.venv\Scripts\python.exe -m pytest tests\test_metrics.py -q
```

## 2. Kiểm tra dữ liệu development

```powershell
Get-Content data\gold\feature_selection_v1\manifest.json
```

Xác nhận hash `train_fs` và `val_fs` khớp manifest. Không thay file và giữ nguyên seed.

## 3. Sinh prediction

Người train phải xuất file theo `phase5_predictions_SCHEMA_EXAMPLE.csv`. B0–B2 chạy trên cùng `val_fs`. B3–B5 để trống nếu chưa có claim-linked labels.

Không dùng `src/models/train_stages.py` hiện tại làm kết quả Phase 5 nếu script còn đọc `dataset_v2/test.parquet`; phải chuyển nó sang `train_fs/val_fs` trước.

## 4. Chạy evaluator

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_phase5_baselines.py `
  path\to\phase5_predictions.csv `
  --config configs\phase5_evaluation.v1.yaml `
  --output-dir reports\phase5 `
  --dataset-name feature_selection_v1_val_fs
```

Output:

```text
reports/phase5/
├── phase5_metrics.json
├── PHASE5_EVALUATION_REPORT.md
├── phase5_pr_curves.png
└── phase5_at_k.png
```

## 5. Đọc paired comparison

Trong `phase5_metrics.json`:

```json
{
  "delta": 0.03,
  "lower": -0.01,
  "upper": 0.08,
  "contains_zero": true
}
```

Kết luận: candidate có point estimate cao hơn 0,03 nhưng CI chứa 0, nên chưa đủ bằng chứng candidate tốt hơn.

## 6. Trước khi nộp

```powershell
.\.venv\Scripts\python.exe -m pytest -q
git status --short
```

Chỉ commit source/config/report cần thiết. Prediction chứa dữ liệu thật hoặc PII không được đẩy lên GitHub public.
