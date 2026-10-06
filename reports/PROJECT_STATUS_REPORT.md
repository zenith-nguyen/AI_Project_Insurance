# BÁO CÁO TIẾN ĐỘ DỰ ÁN

**Dự án:** AI-based Motor-Vehicle Insurance Claim Fraud Detection

**Phụ trách Data & Modeling:** Huy Nhật

**Ngày cập nhật:** 05/10/2026

**Trạng thái:** Đã hoàn thành và kiểm chứng baseline tabular v1; các nhánh mở rộng đang chờ dữ liệu và xác nhận nghiệp vụ.

## 1. Tóm tắt điều hành

Nhóm đã xây dựng được một pipeline Machine Learning có thể tái chạy từ dữ liệu nguồn đến kết quả đánh giá cho bài toán xếp hạng rủi ro gian lận bảo hiểm xe cơ giới. Hệ thống hiện tạo điểm rủi ro để hỗ trợ con người sắp xếp hồ sơ cần xem xét; kết quả mô hình không được dùng để tự động kết luận gian lận hoặc từ chối bồi thường.

Nhánh tabular đã được chạy trên bộ dữ liệu Kaggle `arpan129/insurance-fraud-detection` gồm 1.000 hồ sơ, trong đó có 247 nhãn fraud. Dữ liệu được quản lý qua ba tầng Bronze, Silver và Gold. Gold v2 được cố định thành 700 dòng train, 100 dòng validation và 200 dòng test.

Bốn mô hình đã được so sánh bằng Repeated Stratified Cross-Validation trên tập train: Logistic Regression, Random Forest, XGBoost và LightGBM. XGBoost được chọn theo Average Precision trung bình trên CV. Trên frozen test, mô hình đạt Average Precision 0,559, ROC-AUC 0,825 và Recall@10% 22,4%. Rule baseline đạt Recall@10% 16,3%. Mô hình cải thiện 6,1 điểm phần trăm so với rule baseline, nhưng chưa đạt KPI đề xuất là cải thiện ít nhất 10 điểm phần trăm.

Kết quả hiện tại phù hợp để làm baseline nghiên cứu và minh họa quy trình MLOps. Kết quả chưa đủ căn cứ để sử dụng trong vận hành thực tế vì dữ liệu nhỏ, tỷ lệ fraud của nguồn Kaggle khác production, nguồn gốc nhãn chưa được kiểm chứng và một số tín hiệu mạnh của mô hình chưa có cơ sở nghiệp vụ thuyết phục.

## 2. Mục tiêu và nguyên tắc của hệ thống

Luồng nghiệp vụ dự kiến:

```text
Claim intake
    ↓
Ảnh + dữ liệu hồ sơ + chứng từ
    ↓
Các signal modules
    ↓
Feature aggregation
    ↓
Fraud risk model
    ↓
Probability calibration
    ↓
Risk score + explanation
    ↓
STP candidate / Manual review / SIU review
```

Nguyên tắc đã thống nhất:

- AI hỗ trợ xếp hạng rủi ro và cung cấp lý do giải thích.
- AI không tự động kết luận khách hàng gian lận.
- AI không tự động từ chối hồ sơ chỉ dựa trên điểm mô hình.
- Quyết định cuối cùng thuộc về reviewer, giám định viên hoặc SIU.
- Không ghép CarDD, CORD và Kaggle thành một hồ sơ multimodal khi các nguồn chưa có `claim_id` chung.
- Không tạo số liệu hoặc kết quả mô hình giả để hoàn thiện báo cáo.

## 3. Dữ liệu đã sử dụng

### 3.1. Nhánh tabular

Nguồn dữ liệu:

- Kaggle dataset: `arpan129/insurance-fraud-detection`.
- Workbook: `Worksheet in Case Study question 2.xlsx`.
- Sheet: `Fraud_Detection_decsion tree`.
- Quy mô nguồn: 1.000 dòng, 39 cột.
- Nhãn gốc: `fraud_reported`.
- Phân bố nhãn: 753 non-fraud và 247 fraud.

Silver v1 đã chuẩn hóa:

- Tên cột về `snake_case`.
- Placeholder `?` thành missing value.
- Chuẩn hóa kiểu dữ liệu categorical thành string.
- Parse ngày tháng.
- Thêm `claim_id`, `source_row` và `fraud_label`.
- Kết quả Silver: 1.000 dòng, 42 cột.
- Hash SHA-256 của file được đối chiếu với manifest.

Gold v2 đã được cố định trước preprocessing:

| Split | Số dòng | Vai trò |
|---|---:|---|
| Train | 700 | Audit feature, fit preprocessing, chọn mô hình và calibration |
| Validation | 100 | Chọn ngưỡng hàng đợi review/SIU |
| Test | 200 | Baseline test; đã dùng lại cho sensitivity check và hiện được xem là spent cho feature policy |

Các `claim_id` không trùng giữa ba split. Preprocessing chỉ được fit trên train.

Từ 05/10/2026, 700 dòng train được tách thêm thành `train_fs` 560 dòng và `val_fs` 140 dòng dành riêng cho các quyết định feature tiếp theo. Split này không thay đổi ba file Gold gốc và không trùng với test 200 dòng.

### 3.2. Nhánh ảnh và chứng từ

- CarDD dự kiến dùng cho nhận diện/segmentation hư hại và thử nghiệm ảnh trùng/chỉnh sửa.
- CORD chỉ là nguồn nền cho OCR/document understanding.
- CarDD, CORD và Kaggle chưa có liên kết claim-level.
- CarDD chỉ có trên Google Drive/Colab tại `/content/drive/MyDrive/AI_Project_Insurance/data/bronze/layerA_cardd/`; inspector đã chạy trong Colab ngày 06/10/2026.
- Kết quả inspector ban đầu: 2.753 ảnh JPG, 2.816 sample record và sáu lớp `crack`, `dent`, `glass shatter`, `lamp broken`, `scratch`, `tire flat`.
- Audit xác định 63 ảnh được annotation tham chiếu nhưng tải thiếu; không có filepath trống, ảnh thừa hoặc filename trùng. Đã tải bù từ cùng mirror.
- Kiểm tra cuối: 2.816 sample khớp 2.816 ảnh, không thiếu/thừa, 0 ảnh hỏng và `ready_for_conversion: true`. Báo cáo nằm trên Drive tại `reports/cardd_alignment_final.json`.
- Profile annotation xác định 6.211 damage object được lưu song song: field `detections` chứa box và field `segmentations` chứa cùng box kèm mask `$binary`. Tổng 12.422 box trước đó là đếm lặp hai field. Tất cả sample có annotation và không có tag/split sẵn.
- Mask `$binary` đã được giải mã đúng thành mảng NumPy boolean 2D nén zlib. Toàn bộ 6.211 detection/segmentation pair khớp label và bounding box.
- Conversion YOLO segmentation v2 đã chạy với seed `20261006`: 1.966 ảnh train, 431 validation, 419 test và tổng 6.211 object. Multilabel stratification giữ tỷ lệ từng lớp gần 70/15/15; một nhóm near-duplicate gồm hai ảnh không bị tách chéo split.
- Drive cũ đã hết dung lượng vì `processed/cardd_yolo_v1/images` chứa thêm một bản copy của 2.816 ảnh Bronze. Ngày 07/10/2026, project đã được resume trên Drive mới: Bronze được đọc qua shortcut Drive cũ, conversion v2 được tạo lại ở chế độ `labels-only`, đủ 2.816 labels với split 1.966/431/419, training view được dựng tạm trong `/content` và validator trả `valid: true`. Processed trên Drive mới không chứa bản copy ảnh.
- License yêu cầu prior consent của PIC Lab cho nghiên cứu, authorization cho thương mại, cấm phân phối cho bên thứ ba khi chưa được phép và yêu cầu trích dẫn paper. Repo chưa có bằng chứng prior consent.

## 4. Hạ tầng và pipeline đã hoàn thành

Repo đã được thiết lập với:

- Môi trường ảo Python riêng trong `.venv`.
- Git repository và commit nền tảng `71cfc4b`.
- DVC quản lý metadata của Bronze, Silver và pipeline tạo Gold.
- Cấu hình tách riêng cho feature, model, rule và business assumptions.
- Script dựng Silver, kiểm tra Silver và tạo Gold.
- Pipeline preprocessing bằng `ColumnTransformer` và `Pipeline` của scikit-learn.
- Rule baseline cấu hình ngoài code.
- Huấn luyện Logistic Regression, Random Forest, XGBoost và LightGBM.
- Probability calibration bằng sigmoid/Platt trên out-of-fold train predictions.
- Recall@K, Precision@K, Lift@K, Average Precision, ROC-AUC, Brier score và ECE.
- Bootstrap phân tầng 95% cho các metric chính.
- Ngưỡng `t1`, `t2` được chọn trên validation.
- SHAP global và local cho mô hình được chọn.
- Lệnh chấm điểm file mới và tạo queue candidate.
- Khung Net Value có validation, chưa cho phép chạy khi thiếu chi phí nghiệp vụ.
- Converter và validator YOLO segmentation đã chạy trên dữ liệu thật; training chưa chạy.
- Dữ liệu thô, Parquet, dự đoán từng hồ sơ và model artifact được loại khỏi Git.

Pipeline tabular v1 đã được chạy lại thành công bằng một lệnh. DVC báo dữ liệu và pipeline cập nhật. Lần kiểm thử local gần nhất có 20 test đạt; một test tạo symlink được bỏ qua trên Windows vì cần quyền hệ điều hành và sẽ chạy trong môi trường Colab/Linux.

## 5. Kết quả mô hình đã kiểm chứng

### 5.1. Kết quả trên frozen test

Tập test có 200 hồ sơ, gồm 49 fraud và 151 non-fraud; prevalence là 24,5%.

| Chỉ số | XGBoost được chọn | Rule baseline |
|---|---:|---:|
| Average Precision | 0,559 | 0,424 |
| ROC-AUC | 0,825 | 0,721 |
| Recall@10% | 22,4% | 16,3% |
| Precision@10% | 55,0% | 40,0% |
| Recall@20% | 44,9% | 24,5% |
| Precision@20% | 55,0% | 30,0% |

Mức cải thiện Recall@10% so với rule baseline là 6,1 điểm phần trăm. KPI “cải thiện ít nhất 10 điểm phần trăm” hiện chưa đạt.

### 5.2. Độ bất định

Bootstrap phân tầng 1.000 lần trên frozen test cho kết quả:

| Chỉ số | Điểm ước lượng | Khoảng tin cậy 95% |
|---|---:|---:|
| Average Precision | 0,559 | 0,458–0,691 |
| ROC-AUC | 0,825 | 0,753–0,889 |
| Recall@10% | 22,4% | 12,2%–28,6% |
| Precision@10% | 55,0% | 30,0%–70,0% |

Khoảng tin cậy khá rộng vì test chỉ có 49 fraud. Các khoảng này chỉ phản ánh sampling uncertainty trên dataset hiện tại, chưa bao gồm data drift hoặc khác biệt so với production.

### 5.3. Calibration và ngưỡng vận hành thử nghiệm

- Brier score trên test: 0,139.
- ECE 10 bins trên test: 0,095.
- Ngưỡng được chọn trên validation, không dùng test để chọn ngưỡng.
- Khi áp ngưỡng validation lên test: tổng review queue là 10,5%, SIU candidate 5,0%, STP candidate 89,5% và False Hold Rate 6,6%.

Các con số trên là kết quả nghiên cứu trên Kaggle. Điểm đã calibration vẫn phản ánh prevalence khoảng 24,7% của dữ liệu nguồn, chưa được xác nhận là xác suất fraud ở production.

## 6. Kiểm tra leakage và độ bền của feature

Audit chỉ dùng train đã phát hiện các nhóm cần xem xét:

- `claim_id`, `source_row`, `policy_number`: identifier, không dùng làm feature.
- `fraud_reported`: biểu diễn gốc của target, bắt buộc loại khỏi feature.
- `incident_location`, `insured_zip`: cardinality cao và có rủi ro proxy địa lý.
- `total_claim_amount = injury_claim + property_claim + vehicle_claim` trên 100% dòng train; đây là quan hệ dư thừa cần quản lý.
- Các trường như `incident_severity`, claim components, police report và witnesses cần xác nhận có sẵn tại thời điểm chấm điểm nào.

Một số giá trị của `insured_hobbies` đứng cao trong SHAP. Trên train:

- `cross-fit`: 21 fraud và 2 non-fraud trong 23 dòng.
- `chess`: 28 fraud và 5 non-fraud trong 33 dòng.

Chưa có cơ sở nghiệp vụ để coi sở thích cá nhân là tín hiệu fraud phù hợp cho production. Tuy nhiên, ablation riêng `insured_hobbies` chỉ làm metric thay đổi nhỏ và trái chiều: AP +0,007; ROC-AUC -0,033; Recall@10% -2,0 điểm phần trăm; Recall@20% +2,0 điểm phần trăm. Vì vậy không kết luận mô hình phụ thuộc chủ yếu vào riêng trường này.

Kiểm tra độ nhạy chỉ trên train cho thấy:

| Nhóm feature | Average Precision CV | Recall@10% CV |
|---|---:|---:|
| Baseline nghiên cứu hiện tại | 0,706 | 30,3% |
| Hồ sơ đủ chứng từ, bỏ sở thích, nhân khẩu học, nghề nghiệp, vốn và địa lý | 0,506 | 23,6% |
| Nhóm feature ứng viên lúc tiếp nhận | 0,284 | 10,5% |

Mức giảm CV AP từ 0,706 xuống 0,506 khi bỏ cả nhóm nhân khẩu học/địa lý/sở thích/nghề nghiệp/vốn cho thấy rủi ro nằm ở nhóm proxy rộng. Các trường này cần được xem xét về tính hợp lệ và khả năng tổng quát hóa. Vì vậy baseline hiện tại chưa phù hợp để tự động định tuyến hồ sơ thật.

Sau nhận xét của nhóm, cấu hình `EXCLUDE_BIASED_FEATURES` đã được bổ sung để loại `insured_hobbies`, `insured_zip` và `incident_location`. Hai trường cuối vốn đã bị loại trong baseline; khác biệt thực tế là loại thêm `insured_hobbies`. Toàn bộ CV và frozen test đã được chạy lại, lưu thành một biến thể riêng:

| Chỉ số frozen test | Baseline v1 | Loại biased features |
|---|---:|---:|
| Average Precision | 0,559 | 0,565 |
| ROC-AUC | 0,825 | 0,793 |
| Recall@10% | 22,4% | 20,4% |
| Recall@20% | 44,9% | 46,9% |

Kết quả không giảm đồng loạt: khả năng xếp hạng tổng thể theo ROC-AUC và Recall@10% giảm, trong khi Average Precision tăng nhẹ và Recall@20% tăng. Frozen test 200 dòng đã được dùng hai lần cho so sánh feature policy tính đến 05/10/2026 và không còn untouched cho mục đích này.

Để tách các quyết định tiếp theo khỏi test cũ, DVC đã tạo `feature_selection_v1` chỉ từ 700 dòng train gốc: `train_fs` 560 dòng và `val_fs` 140 dòng, stratified và không trùng `claim_id` với test. Một evaluator cố định đã so sánh các feature profile trên `val_fs`; mọi lựa chọn feature tiếp theo phải dùng protocol này. Sau khi chốt feature và model, cần external test mới cho đánh giá cuối cùng.

## 7. Những phần đang chuẩn bị nhưng chưa được xem là hoàn thành

Nhóm đã thống nhất cần hai checkpoint chấm điểm:

1. `stage1_intake`: chấm điểm ngay khi tiếp nhận hồ sơ.
2. `stage3_complete`: chấm điểm lại sau khi đủ chứng từ.

Config feature cho hai checkpoint đã được tạo. Các profile đã được chạy thăm dò bằng cùng XGBoost trên split feature-selection mới và ghi tại `reports/FEATURE_POLICY.md`; đây là bằng chứng chọn feature trên `val_fs`, không phải kết quả test cuối cùng. Mã huấn luyện/chấm điểm production riêng cho hai checkpoint vẫn chưa được xem là hoàn tất cho đến khi nghiệp vụ xác nhận thời điểm có dữ liệu.

Cần xác nhận các trường `incident_type`, `collision_type`, `number_of_vehicles_involved` và các thông tin sự cố khác có sẵn, đầy đủ đến mức nào ngay tại thời điểm tiếp nhận.

## 8. Những việc chưa thể hoàn thành vì thiếu đầu vào

### 8.1. CarDD / YOLOv8-seg

Cần:

- Lưu bằng chứng prior consent của PIC Lab cho phạm vi đồ án.
- Chạy notebook `CarDD_YOLOv8_Training_v1.ipynb` trên Colab GPU: stage ảnh tạm, preflight, smoke test và baseline YOLOv8n-seg.
- Chọn `best.pt` bằng validation mask mAP50-95; giữ test khóa cho đến khi model/checkpoint được chốt.
- Nếu Colab ngắt, dựng lại `/content` và resume từ `last.pt` trên Drive mới.

### 8.2. Net Value

Cần các giả định được nhóm hoặc giảng viên chấp thuận:

- Tổn thất fraud có thể tránh được.
- Chi phí manual review.
- Chi phí chuyển SIU.
- Chi phí false hold/customer friction.
- Chi phí vận hành AI trên mỗi hồ sơ.

Khung code đã tồn tại nhưng sẽ từ chối tính toán nếu thiếu các giá trị này để tránh tạo kết quả tài chính giả.

### 8.3. Xác nhận nghiệp vụ

Cần làm rõ:

- `fraud_reported` được xác lập bằng điều tra, báo cáo hay quy trình nào.
- Hồ sơ non-fraud có thực sự được xác minh hay chỉ là “không bị báo cáo fraud”.
- Feature nào có sẵn tại intake, sau giám định và sau khi đủ chứng từ.
- Review capacity và SIU capacity thực tế.
- Có cho phép dùng các thuộc tính nhân khẩu học, sở thích, nghề nghiệp và địa lý hay không.

## 9. Kế hoạch đề xuất tiếp theo

### Ưu tiên 1 — Chốt feature theo thời điểm nghiệp vụ

- Làm một data dictionary gồm tên trường, ý nghĩa, nguồn, thời điểm xuất hiện và mức độ tin cậy.
- Chốt feature cho `stage1_intake` và `stage3_complete`.
- Loại các proxy không phù hợp về nghiệp vụ hoặc fairness.
- Dùng `train_fs`/`val_fs` cho mọi so sánh feature policy; không dùng lại frozen test 200 dòng.
- Sau khi feature policy/model được duyệt và khóa, đánh giá một lần trên external test mới.

### Ưu tiên 2 — Hoàn thành nhánh CarDD độc lập

- Kiểm tra dataset và license.
- Chuẩn hóa annotation theo format thực tế.
- Chia train/validation/test theo quy tắc tránh ảnh gần trùng giữa các split.
- Huấn luyện YOLOv8-seg trên GPU.
- Báo cáo mAP50, mAP50:95, per-class AP và lỗi điển hình.
- Giữ kết quả nhánh ảnh độc lập cho đến khi có dữ liệu liên kết claim-level.

### Ưu tiên 3 — Kiểm chứng dữ liệu và nhãn

- Ghi rõ provenance của `fraud_reported`.
- Kiểm tra bias theo các subgroup phù hợp.
- Tìm hoặc xây dựng tập validation gần với bối cảnh Việt Nam/production hơn.
- Nếu xây Layer C synthetic, tách rõ dữ liệu mô phỏng khỏi dữ liệu quan sát thật.

### Ưu tiên 4 — Business evaluation

- Xác nhận review capacity, SIU capacity và chi phí.
- Chạy prevalence scenario 5%, 7% và 10% với giả định được ghi rõ.
- Tính Net Value và uncertainty sau khi có input thật.
- Chỉ chốt `t1`, `t2` vận hành sau khi có dữ liệu gần production.

### Ưu tiên 5 — Hoàn thiện tài liệu và demo

- Tạo data/model cards.
- Tạo sơ đồ kiến trúc và slide trình bày.
- Chuẩn bị demo chấm điểm hồ sơ ở hai checkpoint.
- Ghi rõ human-in-the-loop và giới hạn của SHAP trong giao diện/demo.

## 10. Việc cần các thành viên trong nhóm hỗ trợ

| Người/nhóm hỗ trợ | Thông tin cần cung cấp |
|---|---|
| Chủ dữ liệu CarDD | Đường dẫn ảnh, annotation, metadata và xác nhận quyền dùng |
| Thành viên nghiệp vụ | Data dictionary và thời điểm có sẵn của từng feature |
| Nhóm business | Review/SIU capacity và các chi phí để tính Net Value |
| Nhóm báo cáo | Xác nhận KPI nào là yêu cầu chính thức và KPI nào chỉ là đề xuất |
| Giảng viên/người hướng dẫn | Phản hồi về việc dùng các proxy nhân khẩu học/sở thích và cách diễn giải nhãn |

## 11. Rủi ro và lưu ý bảo mật

- Dataset chỉ có 1.000 dòng và 247 fraud; kết quả có độ bất định cao.
- Prevalence 24,7% khác đáng kể giả định production 5–10%.
- Recall@10% tối đa trên dữ liệu prevalence 24,7% chỉ khoảng 40,8%; không thể áp KPI production trực tiếp mà không điều chỉnh định nghĩa hoặc scenario.
- Các nguồn multimodal chưa liên kết theo claim.
- Không được public raw CarDD khi chưa đáp ứng điều kiện license.
- Kaggle API token đã từng được gửi qua hội thoại; token đó cần được thu hồi và tạo mới. Token không được lưu trong repo hoặc file cấu hình của project.
- Không commit credential, raw restricted data, claim-level predictions hoặc model artifact lên Git public.

## 12. Kết luận

Dự án đã có một nền tảng tabular end-to-end, tái lập được và có kiểm soát leakage tốt hơn baseline notebook ban đầu. XGBoost cho kết quả tốt hơn rule baseline trên frozen test, nhưng chưa đạt KPI cải thiện Recall@10% đề xuất. Phân tích hiện tại cho thấy sự phụ thuộc vào một nhóm proxy rộng cần rà soát về bias và cơ sở nghiệp vụ.

Giá trị quan trọng nhất của giai đoạn hiện tại là pipeline dữ liệu, protocol đánh giá, khả năng tái lập và việc nhận diện đúng các giới hạn. Bước tiếp theo nên tập trung vào feature theo từng checkpoint, provenance của nhãn và dữ liệu CarDD, thay vì tiếp tục tối ưu metric trên cùng dataset nhỏ.

---

### Tài liệu nội bộ liên quan

- `reports/RESULTS.md`: kết quả tabular v1.
- `reports/ROBUSTNESS.md`: kiểm tra độ nhạy feature trên train.
- `reports/leakage/`: báo cáo leakage audit.
- `README.md`: hướng dẫn thiết lập và tái chạy pipeline.
