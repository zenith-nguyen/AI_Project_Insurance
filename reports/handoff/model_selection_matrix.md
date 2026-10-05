# Model Selection Matrix — Train CV

Protocol: Repeated Stratified 5-fold CV × 5 repeats trên 700 dòng train; preprocessing được fit riêng trong từng fold. Tiêu chí chọn chính là Average Precision.

| Model | Mean CV Average Precision | Mean CV Recall@10% | Mean CV ROC-AUC | Quyết định |
|---|---:|---:|---:|---|
| Logistic Regression | 0,671 | 29,7% | 0,867 | Baseline mạnh, không chọn |
| Random Forest | 0,599 | 24,8% | 0,840 | Thấp hơn các ứng viên chính |
| XGBoost | **0,706** | **30,3%** | **0,870** | **Được chọn** |
| LightGBM | 0,653 | 29,6% | 0,837 | Không vượt XGBoost |

XGBoost được chọn vì có Average Precision CV cao nhất; Recall@10% và ROC-AUC CV cũng cao nhất trong bốn cấu hình đã chạy. Không có giant hyperparameter search vì dataset chỉ có 1.000 dòng.
