# Kết quả nhánh tabular v1

Nguồn: Kaggle insurance-fraud-detection; Gold `dataset_v2`. Tập test có 200 hồ sơ, 49 nhãn fraud (24.5%).

## So sánh trên frozen test

| Chỉ số | Mô hình được chọn | Rule baseline |
|---|---:|---:|
| Average Precision | 0.559 | 0.424 |
| ROC-AUC | 0.825 | 0.721 |
| Recall@10% | 22.4% | 16.3% |
| Precision@10% | 55.0% | 40.0% |

Mô hình `xgboost` được chọn bằng Average Precision trung bình của repeated stratified CV trên train. Chênh lệch Recall@10% so với rule là 6.1 điểm phần trăm; chưa đạt mục tiêu đề xuất +10 điểm phần trăm.

## Độ bất định và vận hành

Khoảng tin cậy bootstrap phân tầng 95% cho Recall@10%: 12.2%–28.6%; cho Average Precision: 0.458–0.691. Đây là khoảng tin cậy có điều kiện trên tập test nhỏ, không phản ánh shift dữ liệu.
Brier score: 0.139; ECE 10 bins: 0.095. Điểm xác suất được hiệu chỉnh trên dữ liệu train có tỷ lệ fraud 24,7%; chưa được xác thực như xác suất fraud tại production.
Ngưỡng từ validation tạo tổng hàng đợi review 10.5% trên test (mục tiêu validation 10%); SIU 5.0%, STP candidate 89.5%, false hold 6.6%. Hàng đợi thay đổi khi phân bố dữ liệu đổi.

## Các giới hạn bắt buộc ghi trong đồ án

- CarDD, CORD và Kaggle chưa có claim ID chung; kết quả này chỉ áp dụng cho nhánh tabular.
- Nguồn nhãn `fraud_reported`, thời điểm có sẵn của các feature và chất lượng dữ liệu cần chuyên gia nghiệp vụ xác nhận.
- Kịch bản prevalence 5–10% chỉ là mô phỏng label shift, không phải kiểm định trên dữ liệu production.
- Chưa có chi phí nghiệp vụ để tính Net Value; không suy ra hiệu quả tài chính.
- SHAP giải thích đóng góp vào dự đoán của mô hình, không kết luận khách hàng gian lận hay quan hệ nhân quả.

## Tệp kết quả

- `reports/metrics/tabular_v1.json`: số liệu và metadata chi tiết.
- `reports/leakage/`: audit chỉ trên train.
- `artifacts/shap/tabular_v1/` và `reports/figures/shap_global.png`: giải thích mô hình.
