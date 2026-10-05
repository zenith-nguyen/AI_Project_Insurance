# Metrics v1 — Frozen Test

Gold `dataset_v2`; test gồm 200 hồ sơ, 49 fraud và 151 non-fraud. Model và preprocessing được chọn từ train CV; sigmoid calibration fit bằng out-of-fold train predictions; ngưỡng queue lấy từ validation.

| Metric | XGBoost v1 | Rule baseline |
|---|---:|---:|
| Average Precision | 0,559 | 0,424 |
| ROC-AUC | 0,825 | 0,721 |
| Recall@10% | 22,4% | 16,3% |
| Precision@10% | 55,0% | 40,0% |
| Recall@20% | 44,9% | 24,5% |
| Precision@20% | 55,0% | 30,0% |
| Brier score | 0,139 | Không áp dụng |
| ECE, 10 bins | 0,095 | Không áp dụng |

Bootstrap 95%: AP 0,458–0,691; ROC-AUC 0,753–0,889; Recall@10% 12,2%–28,6%; Precision@10% 30,0%–70,0%. Model hơn rule 6,1 điểm phần trăm Recall@10%, chưa đạt KPI đề xuất +10 điểm.

Không diễn giải calibrated score là xác suất production vì prevalence nguồn là 24,7% và chưa có external validation.
