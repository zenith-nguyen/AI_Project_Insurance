# Báo cáo tiến độ lần 2 — Bản tổng hợp dễ đọc

**Ngày cập nhật:** 13/10/2026
**Trọng tâm:** Data + Baseline + Evaluation v1

## 1. Kết quả chính

Dự án đã hoàn thành data audit và baseline/evaluation v1 cho ba nhánh: dữ liệu bảng, ảnh hư hỏng xe và chứng từ. Nhóm cũng đã có demo consistency rules và NetworkX theo nguyên tắc point-in-time, model registry v1, API contract chạy ở fixture mode và giao diện Claim Review Workbench. Kết quả hiện đủ để chứng minh tính khả thi kỹ thuật và luồng tích hợp prototype, nhưng chưa đại diện cho hiệu quả trên dữ liệu bảo hiểm Việt Nam thực tế.

## 2. Đối chiếu yêu cầu báo cáo

| Yêu cầu | Nội dung đã có | Kết luận |
| --- | --- | --- |
| Data Audit Report | Registry nguồn, kiểm tra file, split, checksum, duplicate và leakage | Đạt |
| Data Dictionary | 39 trường Layer B có ý nghĩa, nguồn, stage và reliability | Đạt |
| EDA/phân tích nguồn | Phân tích CarDD, SROIE, CORD, FUNSD, XFUND, RVL-CDIP và MIDV | Đạt |
| Ground Truth Definition | Định nghĩa nhãn cho ảnh, chứng từ và fraud label; ghi rõ giới hạn provenance | Đạt |
| Data Leakage Check | Phát hiện và xử lý SROIE/FUNSD; ghi rõ test tabular đã bị dùng lại | Đạt |
| Baseline model/process | Tabular, YOLO, DiT, PaddleOCR, rule KIE | Đạt |
| Model Selection Matrix | Có tiêu chí chọn model đặt trước và bằng chứng lựa chọn | Đạt |
| Metrics v1 | Có metric cho tabular, CarDD, classifier, OCR và KIE | Đạt |
| Risk Register v2 | Có rủi ro dữ liệu, license, PII, bias, domain shift và productization | Đạt |
| RAG test | Chưa áp dụng vì nhóm chưa chọn RAG làm baseline | N/A hợp lý |

## 3. Data audit và leakage

Nhóm tổ chức dữ liệu theo Bronze, Processed, Artifacts và Reports. Các nguồn chứng từ đã được đăng ký trong registry thay vì tải rời rạc không có dấu vết.

Hai phát hiện quan trọng nhất:

- SROIE mirror có tám ảnh trùng tuyệt đối giữa raw train và raw test. Nhóm giữ nguyên test, loại ảnh train trùng và tạo processed split 525 train, 93 validation, 361 test. Cả ba cặp split có exact overlap bằng 0.
- FUNSD có hai cây lưu trữ giống nhau, khiến lần kiểm tra đầu đếm 398 thay vì 199 mẫu. Audit đã chọn một canonical root 199 ảnh/199 annotation.

Điều này chứng minh audit không chỉ đếm file mà có khả năng phát hiện lỗi ảnh hưởng trực tiếp đến tính hợp lệ của evaluation.

## 4. Baseline và evaluation v1

### 4.0. Mô hình xếp hạng rủi ro tabular

Bốn model được so sánh bằng Repeated Stratified 5-fold Cross-Validation × 5 repeats trên 700 dòng train. Preprocessing được fit riêng trong từng fold. Average Precision là tiêu chí chọn chính; Recall@10% và ROC-AUC là metric hỗ trợ.

| Model | CV AP | CV Recall@10% | CV ROC-AUC | Quyết định |
| --- | ---: | ---: | ---: | --- |
| Logistic Regression | 0,671 | 29,7% | 0,867 | Baseline đơn giản |
| Random Forest | 0,599 | 24,8% | 0,840 | Không chọn |
| XGBoost | **0,706** | **30,3%** | **0,870** | **Được chọn** |
| LightGBM | 0,653 | 29,6% | 0,837 | Không chọn |

Sau khi chọn bằng CV, XGBoost đạt AP 0,559, ROC-AUC 0,825, Recall@10% 22,4% và Precision@10% 55,0% trên frozen test 200 hồ sơ. Rule baseline đạt Recall@10% 16,3%, nên mức tăng thực tế là 6,1 điểm phần trăm và chưa đạt KPI tương đối +10 điểm.

KPI tuyệt đối Recall@10% ≥ 60% không thể dùng trực tiếp trên dataset prevalence 24,7%; ngay cả model xếp hạng hoàn hảo cũng chỉ có trần khoảng 40,5%. Nhóm phải xác nhận KPI theo prevalence và review capacity của bối cảnh vận hành.

XGBoost là model tốt nhất quan sát được trong bốn cấu hình, nhưng chênh lệch CV AP so với Logistic Regression chỉ là 0,035 và chưa có paired uncertainty comparison. Vì vậy báo cáo không tuyên bố XGBoost đã chứng minh ưu thế ổn định trong production.

### 4.1. Ảnh hư hỏng xe

YOLOv8n-seg được dùng làm baseline. YOLOv8s-seg tăng validation mask mAP50-95 từ 0,5175 lên 0,5284, đạt quy tắc tăng tối thiểu 0,01 đã đặt trước. Checkpoint được khóa bằng SHA-256 trước khi mở test.

Final test chạy đúng một lần trên 419 ảnh/931 đối tượng và đạt mask mAP50-95 0,5140. Các lớp mạnh là `glass shatter` và `tire flat`; các lớp cần cải thiện là `crack`, `dent` và `scratch`.

### 4.2. Phân loại chứng từ

DiT đạt macro-F1 0,9283 và balanced accuracy 0,9281 trên 320 ảnh validation độc lập, cân bằng 20 ảnh cho mỗi lớp. Đây là metric chính để báo cáo; kết quả smoke 0,9626 không được dùng làm metric độc lập.

### 4.3. OCR

PaddleOCR đã xử lý 93 receipt validation, đạt CER 0,4097, WER 0,5592 và thời gian trung bình 28,17 giây/trang trong lần chạy baseline. Pipeline chạy được nhưng chất lượng và latency còn yếu.

### 4.4. Trích xuất thông tin

Rule KIE là baseline có thể giải thích, đạt field micro-F1 khoảng 0,6834 trong phép so sánh cô lập. LayoutLMv3 đạt 0,9214 trên validation cho hai trường `date` và `total`, vượt ngưỡng lựa chọn đặt trước. Checkpoint `checkpoint-264` sau đó được đánh giá đúng một lần trên final test 361 ảnh và đạt field micro-F1 0,8659; Date F1 0,8320; Total F1 0,8995. Inference chỉ chạy một lần; sự cố hàm metric được phục hồi từ prediction còn trong RAM mà không đọc test hoặc inference lại.

### 4.5. Consistency và NetworkX

Consistency rules và NetworkX point-in-time demo đều PASS. Đây là kiểm tra engineering trên dữ liệu synthetic, chứng minh thuật toán và output contract chạy đúng. Chưa có đủ claim/entity/edge thật để đo fraud lift.

## 5. Kiến trúc sản phẩm đã thống nhất

Sản phẩm là một reviewer console gồm bốn màn hình trong cùng ứng dụng:

1. **Claim Workbench:** xử lý hồ sơ hằng ngày.
2. **Evidence & Audit:** xem nguồn gốc và lịch sử của từng kết quả.
3. **Relationship Watch:** xem NetworkX và shared entities.
4. **Model Registry:** xem model version, checkpoint và metric.

UI dùng fixture JSON trong giai đoạn prototype và chuyển sang FastAPI khi inference service hoàn thành. Model chỉ đưa ra evidence và đề xuất route; người duyệt giữ quyền quyết định.

### Model và công nghệ trong hệ thống

| Module | Công nghệ | Hiệu quả hiện tại | Vai trò trong UI |
| --- | --- | --- | --- |
| Tabular risk | XGBoost + sigmoid calibration | Frozen-test AP 0,559; Recall@10% 22,4% | Sắp xếp hàng chờ và explanation |
| Damage image | Ultralytics YOLOv8s-seg | Final-test mask mAP50-95 0,5140 | Hiển thị mask và cảnh báo lớp yếu |
| Document type | Microsoft DiT | Independent macro-F1 0,9283 | Điều hướng tài liệu vào đúng pipeline |
| OCR | PaddleOCR | CER 0,4097; WER 0,5592 | Text và bounding boxes để GĐV đối chiếu |
| KIE | LayoutLMv3 | Final-test field F1 0,8659 trên 361 ảnh | Trích xuất `date` và `total` |
| Consistency | Python rules | Engineering demo PASS | Cờ lệch số tiền, ngày, biển số |
| Relationships | NetworkX | Point-in-time demo PASS | Shared entity và liên kết claim |
| Serving | FastAPI + Docker fixture | API contract và container smoke test PASS | Hợp nhất response theo `claim_id`; live adapters chưa nối |

Đây là kiến trúc nhiều model. Không có một “siêu model” duy nhất đọc toàn bộ ảnh, tài liệu và graph ở giai đoạn hiện tại. Cách tách module giúp kiểm tra từng nguồn bằng chứng, thay model độc lập và hiển thị provenance cho người duyệt.

### Luồng sử dụng của GĐV trong prototype v2

1. Mở hồ sơ từ hàng chờ ưu tiên.
2. Đọc lý do hồ sơ được ưu tiên bằng ngôn ngữ nghiệp vụ.
3. Mở ảnh, chứng từ hoặc quan hệ tương ứng với từng cảnh báo.
4. Đối chiếu bằng chứng gốc; sửa trường OCR/KIE nếu cần.
5. Chọn tiếp tục xử lý, yêu cầu bổ sung hoặc chuyển rà soát chuyên sâu.
6. Ghi lý do; hệ thống lưu người thực hiện, thời gian, model version và thay đổi.

Điểm rủi ro không được gọi là xác suất gian lận nếu chưa được calibration trên prevalence production. UI không có nút “từ chối tự động”.

## 6. Giới hạn cần trình bày trung thực

- Public datasets chưa đại diện đầy đủ cho bảo hiểm xe tại Việt Nam.
- OCR còn yếu; KIE đã hoàn tất final test nhưng hiện mới đánh giá hai field trên receipt công khai.
- CarDD còn ba lớp yếu và cần bằng chứng quyền sử dụng phù hợp.
- `fraud_reported` là observed label có provenance chưa được xác minh đầy đủ.
- NetworkX hiện mới là demo logic, chưa phải fraud model.
- Model registry và fixture API đã có; live model adapters, security/load test và UAT chưa hoàn chỉnh.

## 7. Kế hoạch giai đoạn kế tiếp

### Mốc A — Khóa bằng chứng model hiện tại

1. LayoutLMv3 final test đã hoàn tất đúng một lần trên 361 SROIE test; registry đã cập nhật checkpoint hash và final metric.
2. Không dùng kết quả test để quay lại chọn epoch, sửa alignment hoặc thay hyperparameter.
3. Chốt error analysis theo `date`/`total` trên validation hoặc dữ liệu miền mới, không tối ưu theo final test.

### Mốc B — Đóng gói model cho prototype

1. Tạo model registry chứa model name, version, checkpoint SHA-256, schema, metric và trạng thái gate.
2. Đóng gói adapter riêng cho XGBoost, YOLO, DiT/OCR/LayoutLMv3, consistency và NetworkX.
3. Tạo FastAPI `/health`, `/version` và `/claims/{claim_id}/analyze`.
4. Dùng fixture adapter để nhóm UI phát triển độc lập với GPU; live adapter giữ cùng response schema.

### Mốc C — Clickable MVP

1. Dùng `prototype/insurance_review_console_v2.html` làm UX reference.
2. Hoàn thiện hàng chờ, bằng chứng, corrections, quyết định và audit log.
3. Tạo 5–10 golden claims giả lập hoặc đã ẩn danh có cùng `claim_id` xuyên suốt mọi nguồn.
4. Chạy contract test và end-to-end test trên golden set.

### Mốc D — Cải thiện chất lượng

1. OCR: phân loại lỗi theo ảnh mờ, xoay, chữ nhỏ, dấu phân cách tiền; thử preprocessing và cấu hình OCR trên cùng validation.
2. CarDD: tạo error gallery cho `crack`, `dent`, `scratch`; chỉ cải thiện bằng train/validation hoặc dữ liệu miền mới, không tối ưu theo final test.
3. Tabular: phát triển feature S1–S5 trên `train_fs`/`val_fs`; không dùng lại frozen test để chọn feature.
4. Graph: thu thập entity/edge có timestamp thật rồi mới đánh giá fraud lift.

### Mốc E — Điều kiện trước pilot

1. Dữ liệu bảo hiểm Việt Nam có consent và chính sách PII.
2. Ground-truth/adjudication protocol và external test mới.
3. Security, load, monitoring, rollback và UAT.
4. KPI được xác nhận lại theo prevalence, review capacity, SIU capacity và chi phí thực tế.

## 8. Kết luận

Dự án đã vượt khỏi giai đoạn ý tưởng và đã có các module AI chạy được, metric, audit, bằng chứng lựa chọn model, registry, fixture API và human-review UI. Mốc tiếp theo là nối live adapters, tạo golden claims end-to-end và chuyển fixture UI sang API sử dụng model thật. Production/go-live chỉ được xem xét sau domain validation, security/load test và UAT.

## 9. Nơi kiểm tra bằng chứng kỹ thuật

Nếu cần kiểm tra sâu hơn, không cần đọc toàn bộ thư mục `reports`. Chỉ mở các file sau:

- `CARDD_FINAL_TEST_V1.md`: final test ảnh xe và metric từng lớp.
- `DIT_INDEPENDENT_VALIDATION_V1.md`: validation độc lập của document classifier.
- `DOCUMENT_BASELINE_VALIDATION_V1.md`: OCR và rule KIE baseline.
- `LAYOUTLMV3_CANDIDATE_VALIDATION_V2.md`: kết quả lựa chọn KIE candidate.
- `LAYOUTLMV3_FINAL_TEST_V1.md`: final test KIE 361 ảnh và protocol recovery không inference lại.
- `DATA_LEAKAGE_CHECK_V1.md`: leakage và cách khắc phục.
- `CLAIM_CONSISTENCY_NETWORKX_DEMO_V1.md`: consistency/graph demo.
- `LAYER_B_STAGE_RELIABILITY_DICTIONARY_V1.md`: dictionary 39 trường theo stage.
