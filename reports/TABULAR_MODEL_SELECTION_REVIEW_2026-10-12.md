# Rà soát nội dung lựa chọn mô hình tabular

## Nhận xét chung

Bản thảo của nhóm có bố cục và lập luận đúng hướng: xuất phát từ năng lực review giới hạn, dùng metric phù hợp với bài toán xếp hạng, so sánh baseline với ứng viên phức tạp hơn và không đồng nhất “tốt nhất trong số đã thử” với “đã đạt KPI”. Tuy nhiên cần sửa một số điểm để khớp với bằng chứng đã chạy.

## Các điểm cần sửa

### 1. Tách kết quả cross-validation và frozen test

`Recall@10% = 30,3%` là trung bình từ repeated cross-validation trên 700 dòng train. Đây là số dùng để **chọn model**.

Sau khi chọn XGBoost, kết quả trên frozen test 200 hồ sơ là:

| Metric | XGBoost | Rule baseline |
| --- | ---: | ---: |
| Average Precision | 0,559 | 0,424 |
| ROC-AUC | 0,825 | 0,721 |
| Recall@10% | 22,4% | 16,3% |
| Precision@10% | 55,0% | 40,0% |

Vì vậy không được dùng 30,3% như kết quả cuối cùng của model.

### 2. KPI Recall@10% ≥ 60% không khả thi trên dataset hiện tại

Dataset có prevalence fraud khoảng 24,7%. Nếu chỉ được review 10% hồ sơ thì ngay cả khi xếp hạng hoàn hảo, Recall@10% tối đa chỉ là:

`10% / 24,7% ≈ 40,5%`.

Trên frozen test prevalence 24,5%, trần tương ứng khoảng 40,8%. KPI tuyệt đối 60% chỉ có thể đánh giá trong một bối cảnh prevalence thấp hơn hoặc khi tăng review capacity. Ví dụ, với prevalence 24,7%, muốn Recall 60% thì queue tối thiểu về mặt toán học đã khoảng 14,8%, kể cả khi model hoàn hảo.

Đề xuất thay KPI hiện tại bằng một trong hai cách:

- KPI tương đối: XGBoost phải tăng Recall@10% ít nhất 10 điểm phần trăm so với rule baseline; hoặc
- KPI vận hành theo scenario: đặt Recall@K cho prevalence và review capacity đã được nghiệp vụ xác nhận.

Theo KPI tương đối đang dùng, XGBoost tăng 6,1 điểm phần trăm và **chưa đạt mục tiêu +10 điểm**.

### 3. Hold-out test và calibration đã được thực hiện

Bản thảo không nên viết “giai đoạn tiếp theo sẽ đánh giá trên hold-out test” vì frozen test đã được chạy. Calibration cũng đã được đo:

- Brier score: 0,139;
- ECE 10 bins: 0,095.

Frozen test đã được dùng lại cho một phân tích feature-policy, nên không còn untouched cho lựa chọn feature tiếp theo. Sau khi thêm S1–S5 hoặc thay feature policy, phải dùng `train_fs`/`val_fs` để phát triển và một external test mới để đánh giá cuối.

### 4. Mức cải thiện so với Logistic Regression còn nhỏ

XGBoost có AP 0,706 so với Logistic Regression 0,671, chênh lệch 0,035. XGBoost là model tốt nhất quan sát được trong bốn cấu hình, nhưng chưa có paired confidence interval hoặc statistical comparison giữa hai model trên cùng fold. Vì vậy nên viết “đạt trung bình cao nhất” thay cho “chứng minh vượt trội ổn định”.

### 5. Làm rõ nguyên tắc chọn model

Trong protocol hiện tại, Average Precision là tiêu chí lựa chọn chính; Recall@10% và ROC-AUC là metric hỗ trợ. Nếu nhóm tuyên bố Recall@10% là KPI quan trọng nhất, nên viết rõ quy tắc theo thứ tự:

1. loại model không đáp ứng data/leakage gate;
2. chọn model có AP trung bình cao nhất;
3. dùng Recall@10% và độ ổn định giữa folds để kiểm tra khả năng vận hành;
4. chỉ chọn model phức tạp hơn khi mức tăng đủ lớn và rủi ro bias được chấp nhận.

Trong lần chạy hiện tại, cả AP và Recall@10% đều cùng chọn XGBoost nên quyết định không thay đổi.

## Phiên bản nội dung đề xuất

### Mục tiêu và protocol

Mô hình tabular tạo điểm ưu tiên để xếp hạng hồ sơ cho hàng đợi rà soát, không tự kết luận gian lận. Do năng lực rà soát giới hạn ở khoảng 10% số hồ sơ, nhóm theo dõi Recall@10% và Precision@10%. Average Precision được khóa làm tiêu chí lựa chọn chính vì đánh giá chất lượng xếp hạng trên toàn dải threshold trong bài toán mất cân bằng.

Bốn mô hình Logistic Regression, Random Forest, XGBoost và LightGBM được đánh giá bằng Repeated Stratified 5-fold Cross-Validation × 5 repeats trên 700 dòng train. Preprocessing được fit riêng trong từng fold.

| Mô hình | CV Average Precision | CV Recall@10% | CV ROC-AUC | Quyết định |
| --- | ---: | ---: | ---: | --- |
| Logistic Regression | 0,671 | 29,7% | 0,867 | Baseline |
| Random Forest | 0,599 | 24,8% | 0,840 | Không chọn |
| XGBoost | **0,706** | **30,3%** | **0,870** | **Được chọn** |
| LightGBM | 0,653 | 29,6% | 0,837 | Không chọn |

XGBoost có trung bình cao nhất trên cả ba metric và được chọn làm candidate tabular v1. Logistic Regression được giữ làm baseline đơn giản. Chênh lệch AP giữa XGBoost và Logistic Regression là 0,035; do chưa có paired uncertainty comparison, kết luận phù hợp là XGBoost tốt nhất trong các cấu hình đã thử, không phải đã chứng minh ưu thế ổn định trong production.

### Kết quả frozen test

Sau khi lựa chọn bằng CV, XGBoost đạt AP 0,559, ROC-AUC 0,825, Recall@10% 22,4% và Precision@10% 55,0% trên frozen test 200 hồ sơ. Rule baseline đạt Recall@10% 16,3%, vì vậy model cải thiện 6,1 điểm phần trăm nhưng chưa đạt KPI tương đối +10 điểm.

KPI tuyệt đối Recall@10% ≥ 60% không thể áp trực tiếp cho dataset prevalence 24,7%, vì trần lý thuyết chỉ khoảng 40,5%. Nhóm cần xác nhận lại KPI theo production prevalence và review capacity.

### Giới hạn và bước tiếp theo

Nhãn `fraud_reported` được dùng như observed fraud status; provenance chưa đủ để xem là verified actual fraud. Model hiện có thể học khả năng một hồ sơ bị báo cáo/phát hiện là gian lận, chưa chứng minh xác suất gian lận thực tế.

Frozen test đã được dùng lại cho sensitivity analysis và không còn được dùng để chọn feature. Các đặc trưng S1–S5 mới sẽ được phát triển trên `train_fs`/`val_fs`. Sau khi khóa feature policy, model và calibration, nhóm cần một external test mới có provenance rõ hơn.
