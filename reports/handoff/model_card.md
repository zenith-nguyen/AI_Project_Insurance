# Model Card — Tabular Fraud Risk v1

## Mục đích

Model xếp hạng rủi ro fraud để hỗ trợ reviewer/SIU ưu tiên hồ sơ. Output không phải bằng chứng gian lận, không tự động từ chối bồi thường và luôn cần human-in-the-loop.

## Dữ liệu và pipeline

- Kaggle `arpan129/insurance-fraud-detection`: 1.000 hồ sơ, 753 non-fraud và 247 fraud.
- Silver: 1.000 × 42; Gold v2: train 700, validation 100, test 200.
- Pipeline baseline: Bronze → Silver → Gold → train-only preprocessing → CV model selection → sigmoid calibration → frozen test → SHAP. Frozen test sau đó đã được dùng lần hai cho sensitivity check nên không còn untouched cho quyết định feature policy.
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

- Một số category của `insured_hobbies` đứng cao trong SHAP, nhưng bỏ riêng trường này chỉ làm metric thay đổi nhỏ và trái chiều: AP +0,007; ROC-AUC -0,033; Recall@10% -2,0 điểm phần trăm; Recall@20% +2,0 điểm phần trăm. Khi bỏ cả nhóm proxy nhân khẩu học/địa lý/sở thích/nghề nghiệp/vốn, CV AP giảm từ 0,706 xuống 0,506. Vì vậy rủi ro nằm ở nhóm proxy rộng, không có cơ sở trình bày `insured_hobbies` như chỉ báo fraud thực tế.
- Frozen test 200 dòng đã được dùng hai lần cho so sánh feature policy tính đến 05/10/2026. Mọi quyết định feature tiếp theo dùng `train_fs`/`val_fs`; cần external test mới sau khi chốt policy/model.
- Prevalence nguồn là 24,7%, khác giả định production 5–10%. Trần Recall@10% trên toàn nguồn chỉ khoảng 40,5%; KPI 60% không thể đánh giá trực tiếp trên dataset này.
- Quy trình xác lập `fraud_reported` chưa được kiểm chứng. Metadata Mendeley nói có đánh giá thủ công/tự động, nhưng không cung cấp adjudication protocol có thể audit; vì vậy dự án gọi đây là observed fraud status và chấm reliability 3/8 (Thấp). Xem `reports/FRAUD_LABEL_PROVENANCE_V1.md`.
- Test chỉ có 49 fraud; chưa có external validation hoặc dữ liệu Việt Nam.
- CarDD/CORD chưa liên kết claim-level với dữ liệu tabular. Chưa có Net Value hoặc production-readiness claim.
