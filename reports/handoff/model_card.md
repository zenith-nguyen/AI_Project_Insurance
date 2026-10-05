# Model Card — Tabular Fraud Risk v1

## Mục đích

Model xếp hạng rủi ro fraud để hỗ trợ reviewer/SIU ưu tiên hồ sơ. Output không phải bằng chứng gian lận, không tự động từ chối bồi thường và luôn cần human-in-the-loop.

## Dữ liệu và pipeline

- Kaggle `arpan129/insurance-fraud-detection`: 1.000 hồ sơ, 753 non-fraud và 247 fraud.
- Silver: 1.000 × 42; Gold v2: train 700, validation 100, test 200.
- Pipeline: Bronze → Silver → Gold → train-only preprocessing → CV model selection → sigmoid calibration → frozen test → SHAP.
- So sánh Logistic Regression, Random Forest, XGBoost và LightGBM bằng 5-fold CV lặp 5 lần. XGBoost có Average Precision CV cao nhất nên được chọn.

## Frozen-test metrics

| Metric | Kết quả |
|---|---:|
| Average Precision | 0,559 |
| ROC-AUC | 0,825 |
| Recall@10% / Precision@10% | 22,4% / 55,0% |
| Recall@20% / Precision@20% | 44,9% / 55,0% |
| Brier score | 0,139 |
| ECE, 10 bins | 0,095 |

## Known limitations

- SHAP cho thấy model dựa mạnh vào `insured_hobbies`; đây có thể là bias của Kaggle, không phải chỉ báo fraud thực tế. Khi loại thêm trường này: AP 0,565, ROC-AUC 0,793, Recall@10% 20,4%, Recall@20% 46,9%.
- Prevalence nguồn là 24,7%, khác giả định production 5–10%. Trần Recall@10% trên toàn nguồn chỉ khoảng 40,5%; KPI 60% không thể đánh giá trực tiếp trên dataset này.
- Quy trình xác lập `fraud_reported` chưa được kiểm chứng.
- Test chỉ có 49 fraud; chưa có external validation hoặc dữ liệu Việt Nam.
- CarDD/CORD chưa liên kết claim-level với dữ liệu tabular. Chưa có Net Value hoặc production-readiness claim.
