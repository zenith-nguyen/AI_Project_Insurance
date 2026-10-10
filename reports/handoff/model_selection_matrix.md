# Model Selection Matrix — Train CV

Protocol: Repeated Stratified 5-fold CV × 5 repeats trên 700 dòng train; preprocessing được fit riêng trong từng fold. Tiêu chí chọn chính là Average Precision.

| Model | Mean CV Average Precision | Mean CV Recall@10% | Mean CV ROC-AUC | Quyết định |
|---|---:|---:|---:|---|
| Logistic Regression | 0,671 | 29,7% | 0,867 | Baseline mạnh, không chọn |
| Random Forest | 0,599 | 24,8% | 0,840 | Thấp hơn các ứng viên chính |
| XGBoost | **0,706** | **30,3%** | **0,870** | **Được chọn** |
| LightGBM | 0,653 | 29,6% | 0,837 | Không vượt XGBoost |

XGBoost được chọn vì có Average Precision CV cao nhất; Recall@10% và ROC-AUC CV cũng cao nhất trong bốn cấu hình đã chạy. Không có giant hyperparameter search vì dataset chỉ có 1.000 dòng.

## CarDD segmentation — Validation

Protocol dùng cùng train/validation split, ảnh 640, batch 8, seed 20261007 và tối đa 100 epoch. Quy tắc đặt trước: chỉ chọn model lớn hơn khi tăng ít nhất `0,0100` validation mask mAP50-95.

| Model | Validation mask mAP50-95 | Chênh lệch | Quyết định |
|---|---:|---:|---|
| YOLOv8n-seg baseline v2 | 0,5175 | — | Baseline |
| YOLOv8s-seg candidate v1 | **0,5284** | **+0,0109** | **Được chọn** |

Checkpoint YOLOv8s đã khóa bằng SHA-256 `6c0d828760a427d48623653dcd6fffeb1cf591045d9ce8b8684a1d0f5f89420b`. Test CarDD chưa được dùng tại thời điểm cập nhật.
