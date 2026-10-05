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

## Chi phí của việc loại các feature có nguy cơ bias

Cấu hình `EXCLUDE_BIASED_FEATURES: true` loại `insured_hobbies`, `insured_zip` và `incident_location`. Hai cột sau vốn đã thuộc danh sách loại trừ; thay đổi thực tế so với baseline v1 là loại thêm `insured_hobbies`. Biến thể được chọn lại mô hình bằng cùng protocol CV trên train và đánh giá trên cùng frozen test.

| Chỉ số | Baseline v1 | Loại biased features | Thay đổi |
|---|---:|---:|---:|
| Average Precision | 0.559 | 0.565 | +0.007 |
| ROC-AUC | 0.825 | 0.793 | -0.033 |
| Recall@10% | 22.4% | 20.4% | -2.0 điểm % |
| Recall@20% | 44.9% | 46.9% | +2.0 điểm % |

Việc bỏ riêng `insured_hobbies` tạo thay đổi nhỏ và không cùng chiều: AP +0,007; ROC-AUC -0,033; Recall@10% -2,0 điểm phần trăm; Recall@20% +2,0 điểm phần trăm. Bằng chứng này không hỗ trợ kết luận rằng mô hình phụ thuộc chủ yếu vào riêng trường sở thích.

## Protocol feature-selection từ 05/10/2026

Một split mới được tạo chỉ từ 700 dòng train gốc: `train_fs` có 560 dòng và `val_fs` có 140 dòng. Hai tập này không trùng `claim_id` với nhau hoặc với test 200 dòng; hash được khóa trong manifest `feature_selection_v1`.

> Frozen test used twice for feature-policy comparison as of 2026-10-05 — no longer untouched for that purpose; use val_fs for any further feature-selection decisions.

Mọi so sánh feature policy tiếp theo dùng `train_fs`/`val_fs`. Sau khi chốt feature và model, cần một external test mới cho đánh giá cuối cùng.

## Known Limitations

- Với prevalence 24,7% của toàn dataset, trần lý thuyết của Recall@10% là `0,10 / 0,247 ≈ 40,5%`; trên frozen test prevalence 24,5%, con số tương ứng là khoảng 40,8%. Vì vậy mục tiêu Recall@10% = 60% không thể đạt trực tiếp trên dataset này nếu không chuyển sang một giả định prevalence khác.
- Nguồn gốc và quy trình xác lập nhãn `fraud_reported` chưa được kiểm chứng. Nhãn này có thể phản ánh fraud được báo cáo/phát hiện thay vì toàn bộ fraud thực tế.
- Một số category của `insured_hobbies` đứng cao trong SHAP, nhưng ablation riêng trường này chỉ làm metric thay đổi nhỏ và trái chiều. Mức giảm CV AP lớn hơn, từ 0,706 xuống 0,506, xảy ra khi bỏ cả nhóm proxy nhân khẩu học/địa lý/sở thích/nghề nghiệp/vốn. Vì vậy phát hiện cần diễn giải là phụ thuộc vào nhóm proxy rộng; không trình bày `insured_hobbies` như một chỉ báo gian lận thực tế.
- CarDD, CORD và Kaggle chưa có claim ID chung; kết quả này chỉ áp dụng cho nhánh tabular.
- Kịch bản prevalence 5–10% chỉ là mô phỏng label shift, không phải kiểm định trên dữ liệu production.
- Chưa có chi phí nghiệp vụ để tính Net Value; không suy ra hiệu quả tài chính hay production readiness.

## Tệp kết quả

- `reports/metrics/tabular_v1.json`: số liệu và metadata chi tiết.
- `reports/metrics/tabular_bias_excluded_v1.json`: kết quả chi tiết của biến thể loại biased features.
- `reports/FEATURE_POLICY.md`: so sánh ứng viên trên `val_fs`, không đọc test cũ.
- `reports/leakage/`: audit chỉ trên train.
- `artifacts/shap/tabular_v1/` và `reports/figures/shap_global.png`: giải thích mô hình.

Train-only CV Average Precision theo nhóm feature: mô hình nghiên cứu đầy đủ 0.706, hồ sơ đủ chứng từ 0.506, lúc tiếp nhận 0.284. Chưa xác nhận thời điểm có sẵn của mọi trường.
