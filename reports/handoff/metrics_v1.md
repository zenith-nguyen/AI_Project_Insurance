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

Trạng thái protocol: test 200 dòng này sau đó đã được dùng lần hai cho sensitivity check loại `insured_hobbies`, nên không còn untouched cho quyết định feature policy. Mọi lựa chọn feature tiếp theo dùng `train_fs`/`val_fs`; cần external test mới sau khi chốt policy/model.

## CarDD validation — chưa phải final test

| Metric | YOLOv8n | YOLOv8s được chọn |
|---|---:|---:|
| Mask mAP50-95 | 0,5175 | **0,5284** |
| Mask mAP50 | 0,6974 | **0,6980** |
| Box mAP50-95 | 0,5377 | **khoảng 0,5570** |

YOLOv8s tăng `0,010865` mask mAP50-95 và vượt ngưỡng chọn model `0,010000`. Đây là validation metric trên 431 ảnh/935 instance. Final test 419 ảnh/931 instance chưa chạy, vì vậy không được ghi các số trên là test performance.
