# Phần bổ sung Báo cáo tiến độ đợt 2 — Mục 4 đến 11

**Đề tài:** Hệ thống AI chấm điểm rủi ro gian lận cho hồ sơ bồi thường bảo hiểm vật chất xe ô tô  
**Ngày cập nhật:** 13/10/2026  
**Phạm vi tuyên bố:** Technical PoC hỗ trợ người duyệt; chưa đủ bằng chứng để triển khai production hoặc tự động từ chối hồ sơ.

Phần này thay cho các dòng “khung tiêu đề”, “[Bổ sung]” và “cần xác nhận phạm vi” trong bản PDF ngày 13/10/2026. Tên artifact trong ngoặc là nơi kiểm chứng số liệu trong repository.

## 4. Ground Truth Definition và Citation Policy

### 4.1. Nguyên tắc chung

Ground truth được định nghĩa riêng theo từng tác vụ. Nhãn của dữ liệu công khai chỉ là chuẩn đánh giá nghiên cứu trong đúng miền dữ liệu đó; không tự động trở thành ground truth của nghiệp vụ bảo hiểm Việt Nam. Mỗi kết quả phải lưu dataset/split, phiên bản schema, thời điểm đánh giá, model/checkpoint và quy tắc chuẩn hóa. Test không được dùng để chọn model, sửa threshold hoặc điều chỉnh mapping.

### 4.2. Ground truth theo tác vụ

| Tác vụ | Ground truth dùng trong PoC | Metric chính | Giới hạn |
|---|---|---|---|
| Tabular risk ranking | `fraud_reported=Y/N`, được diễn giải là **observed fraud status** | Average Precision, Recall@K, Precision@K, ROC-AUC | Chưa có bằng chứng Y/N được xác lập bằng quy trình điều tra chính thức; N có thể chứa fraud chưa phát hiện |
| Car damage segmentation | Polygon và class vùng hư hỏng của CarDD: crack, dent, glass shatter, lamp broken, scratch, tire flat | Mask mAP50-95 | Nhãn công khai, chưa đại diện ảnh claim Việt Nam |
| Document classification | Class do RVL-CDIP cung cấp, 16 lớp | Macro-F1, balanced accuracy | Taxonomy không phải taxonomy chứng từ bảo hiểm Việt Nam |
| OCR | Chuỗi transcription từ annotation nguồn sau quy tắc Unicode/khoảng trắng đã khóa | CER, WER | Không sửa ground truth sau khi xem prediction |
| KIE | Tên trường, giá trị và vùng/entity khi nguồn có cung cấp | Precision, recall, field micro-F1 | SROIE hiện chỉ đánh giá `date` và `total` |
| Consistency rules | Giá trị chuẩn do reviewer xác nhận giữa claim và chứng từ | Tỷ lệ rule đúng/sai theo từng loại đối chiếu | Hiện mới có engineering demo; chưa có benchmark claim thật |
| Relationship graph | Entity/edge có `claim_id`, nguồn và timestamp hợp lệ | Feature correctness; fraud lift khi có nhãn thật | NetworkX hiện là bộ tạo feature, chưa phải fraud classifier |
| Media authenticity | Provenance có chữ ký/manifest được xác minh hoặc nhãn benchmark có nguồn rõ | Precision/recall theo từng nhóm biến đổi | Thiếu metadata không chứng minh ảnh thật; chưa có pixel-forensic benchmark đúng miền |

Đối với dữ liệu bảo hiểm thật, tập evaluation quan trọng cần hai người gán nhãn độc lập và một reviewer nghiệp vụ xử lý bất đồng. Mọi chỉnh sửa ground truth sau evaluation phải tạo version mới; không ghi đè kết quả cũ và không đưa PII thô vào báo cáo/source control.

### 4.3. Citation Policy

Core product hiện không dùng RAG hoặc LLM bên ngoài. Tuy vậy, mọi diễn giải hiển thị cho người duyệt phải truy được về ít nhất một `evidence_id`, trường dữ liệu nguồn, rule ID hoặc model version. Nội dung không có bằng chứng được đánh dấu `unsupported/unknown`; hệ thống không được tự bổ sung số tiền, ngày, biển số hay kết luận gian lận.

Nếu mở RAG trong tương lai, citation ground truth phải chứa `document_id`, page/region và đoạn nguồn hỗ trợ từng mệnh đề. Câu trả lời thiếu nguồn, trích sai trang hoặc mâu thuẫn nguồn được tính là citation failure.

**Bằng chứng:** `reports/GROUND_TRUTH_DEFINITION_V1.md`, `reports/FRAUD_LABEL_PROVENANCE_V1.md`.

## 5. Data Leakage Check

### 5.1. Kiểm tra đã thực hiện

- Tách train/validation/test trước khi training; preprocessing được fit trong từng fold hoặc chỉ trên train.
- Kiểm exact image overlap bằng SHA-256 giữa các split.
- Kiểm số mẫu, schema, ảnh hỏng, file thiếu/orphan label và invalid annotation.
- Kiểm checksum/ZIP đối với nguồn document; kiểm cân bằng sample RVL-CDIP.
- Kiểm test có bị dùng để lựa chọn model, threshold hoặc feature policy hay không.

### 5.2. Kết quả và remediation

| Nguồn | Phát hiện | Xử lý/trạng thái |
|---|---|---|
| Tabular Layer B | Preprocessing được fit trong từng CV fold. Frozen test 200 dòng đã dùng lại cho sensitivity analysis feature-policy | Test không còn “untouched” cho lựa chọn feature. Mọi phát triển tiếp theo dùng `train_fs/val_fs`; cần external test mới |
| CarDD | Split train 1.966, validation 431, test 419 được khóa trước training; không dùng test để chọn YOLO | Model selection trên validation; final test chạy đúng một lần và khóa bằng checkpoint/report hash |
| CORD v2 | Không có exact duplicate chéo train/validation/test | PASS |
| SROIE raw | Tám ảnh trùng tuyệt đối giữa train và test | Giữ test 361; loại tám row train trùng; group split SHA-256 thành 525 train/93 validation; overlap ba cặp bằng 0 |
| FUNSD | Hai cây lưu trữ của cùng bộ 199 mẫu làm lần đếm đầu thành 398 | Chọn một canonical root: 199 ảnh và 199 annotation |
| XFUND | Không có exact duplicate train/validation; checksum và ZIP hợp lệ | PASS |
| RVL-CDIP | Sample 1.600 ảnh cân bằng 100 ảnh/lớp; sample train có thể overlap dữ liệu upstream của DiT | Không dùng smoke sample làm independent validation; đo lại 320 ảnh từ official validation |

Các kiểm tra còn mở là near-duplicate bằng perceptual hash/embedding, trùng nội dung sau crop/resize/OCR và leakage theo `claim_id`, customer, vehicle, incident. Khi có dữ liệu claim thật, toàn bộ ảnh và chứng từ của cùng claim phải nằm trong cùng split.

**Bằng chứng:** `reports/DATA_LEAKAGE_CHECK_V1.md`, `reports/SROIE_PROCESSED_SPLIT_RESULT_V1.md`, `reports/CARDD_FINAL_TEST_V1.md`.

## 6. Baseline model và baseline process

### 6.1. Vai trò từng baseline

| Nhánh | Baseline | Candidate/phiên bản đang dùng | Vai trò trong sản phẩm |
|---|---|---|---|
| Tabular risk | Logistic Regression và business rule | XGBoost v1 | Xếp hạng hồ sơ cần xem trước; không tự kết luận gian lận |
| Damage segmentation | YOLOv8n-seg | YOLOv8s-seg | Khoanh vùng loại hư hỏng trên ảnh xe |
| Document classification | DiT pretrained | Giữ DiT làm baseline kỹ thuật | Phân biệt loại chứng từ trước OCR/KIE |
| OCR | PaddleOCR | PaddleOCR baseline v1 | Đọc chữ và vị trí từ ảnh chứng từ |
| KIE | Rule KIE v1 | LayoutLMv3 `checkpoint-264` | Trích xuất `date` và `total` trên SROIE |
| Consistency | Versioned Python rules | Consistency v1 | So sánh claim amount/date/plate với trường chứng từ |
| Relationship | NetworkX point-in-time features | NetworkX v1 | Tìm entity dùng chung, component và quan hệ hai hop |
| Media authenticity | Metadata/hash/C2PA khi có tool | Authenticity v2 | Tạo tín hiệu provenance/reuse; không tuyên bố chắc chắn ảnh AI hay ảnh thật |

### 6.2. Baseline process

1. Chạy data gate và leakage gate trước training.
2. Chia train/validation/test hoặc CV theo protocol đã khóa.
3. Fit preprocessing chỉ trên train/fold train.
4. Chọn model/checkpoint bằng CV hoặc validation theo rule đặt trước.
5. Khóa checkpoint bằng SHA-256 và ghi selection report.
6. Mở final test đúng một lần; không tối ưu lại theo test.
7. Đưa output về cùng `claim_id`; module thiếu đầu vào trả `partial/unknown` thay vì tự suy diễn.
8. Người duyệt xem bằng chứng, sửa field nếu cần và lưu quyết định cùng audit trail.

### 6.3. Kết quả baseline chính

- Tabular frozen test: XGBoost AP 0,559; Recall@10% 22,4%. Business rule AP 0,424; Recall@10% 16,3%.
- CarDD: YOLOv8s final-test mask mAP50-95 0,5140 trên 419 ảnh.
- DiT independent validation: macro-F1 0,9283 trên 320 ảnh.
- PaddleOCR: CER 0,4097; WER 0,5592; trung bình 28,17 giây/trang trên 93 trang.
- Rule KIE: micro-F1 0,6776. LayoutLMv3 final test: field micro-F1 0,8659 trên 361 ảnh.

**Bằng chứng:** `reports/RESULTS.md`, `reports/CARDD_BASELINE_V2_RESULTS.md`, `reports/DOCUMENT_BASELINE_VALIDATION_V1.md`, `reports/LAYOUTLMV3_FINAL_TEST_V1.md`.

## 7. Model Selection Matrix và Build/Buy/API/RAG Justification

### 7.1. Model Selection Matrix

| Quyết định | Các phương án | Tiêu chí khóa trước | Kết quả | Quyết định |
|---|---|---|---|---|
| Tabular | Logistic Regression, Random Forest, XGBoost, LightGBM | Repeated stratified 5-fold CV × 5; chọn AP trung bình cao nhất | XGBoost AP 0,706; Recall@10% 30,3%; ROC-AUC 0,870 | Chọn XGBoost; giữ Logistic làm baseline |
| Damage | YOLOv8n-seg, YOLOv8s-seg | Chỉ chọn model lớn khi tăng ≥0,0100 validation mask mAP50-95 | YOLOv8s 0,5284 so với 0,5175; tăng 0,0109 | Chọn YOLOv8s; chấp nhận model lớn/chậm hơn |
| KIE | Rule KIE, LayoutLMv3 | Candidate phải tăng field F1 ≥0,02 trên validation, test vẫn khóa | LayoutLMv3 0,9214 so với rule comparable 0,6834 | Chọn checkpoint-264; final test 0,8659 |
| Document classification | Rule/template, pretrained DiT | Macro-F1 trên validation độc lập và khả năng tái sử dụng | DiT macro-F1 0,9283 | Giữ DiT pretrained cho PoC |
| OCR | OCR cloud/API, PaddleOCR local | Baseline chạy offline, đo CER/WER/latency trước khi cân nhắc mua | PaddleOCR đã chạy nhưng CER/WER và latency còn yếu | Giữ làm baseline; chưa chốt production engine |

### 7.2. Build/Buy/API/RAG Justification

| Hướng | Quyết định hiện tại | Lý do |
|---|---|---|
| Build | Chọn cho XGBoost, rules, NetworkX, orchestration/API và reviewer UI | Logic nghiệp vụ, schema, audit trail và feature policy cần kiểm soát/version hóa nội bộ |
| Reuse open-source pretrained | Chọn cho YOLO, DiT, PaddleOCR, LayoutLMv3 rồi fine-tune/evaluate khi phù hợp | Giảm chi phí xây từ đầu và có benchmark tái lập; vẫn cần license, domain validation và artifact hash |
| Buy/cloud API | Chưa chọn làm core baseline | Có thể giúp OCR/document processing nhưng phát sinh chi phí, vendor lock-in, PII/data residency và khó tái lập; chỉ đánh giá khi baseline local không đạt SLA |
| External LLM API | Không dùng trong suy luận core | Core pipeline chạy bằng model/checkpoint của nhóm; tránh phụ thuộc LLM cho kết luận gian lận và tránh hallucination |
| RAG | N/A ở Evaluation v1 | Bài toán hiện tại không cần truy xuất knowledge base để tạo risk score; mở RAG chỉ khi có use case hỏi đáp policy/SOP có citation |

Kết luận lựa chọn hiện tại là **Conditional Go cho Technical PoC**. XGBoost là model tabular tốt nhất trong bốn cấu hình đã thử, nhưng lợi thế CV AP so với Logistic Regression chỉ 0,035 và chưa có paired uncertainty comparison. Không tuyên bố mô hình đã vượt trội ổn định hoặc production-ready.

**Bằng chứng:** `reports/handoff/model_selection_matrix.md`, `reports/CARDD_MODEL_SELECTION_V1.md`, `reports/TABULAR_MODEL_SELECTION_REVIEW_2026-10-12.md`.

## 8. Metrics v1

### 8.1. Tabular risk — frozen test 200 hồ sơ, 49 Y

| Metric | XGBoost v1 | Rule baseline | Diễn giải |
|---|---:|---:|---|
| Average Precision | 0,559 | 0,424 | Metric chính cho dữ liệu mất cân bằng |
| ROC-AUC | 0,825 | 0,721 | Metric hỗ trợ |
| Recall@10% | 22,4% | 16,3% | XGBoost tăng 6,1 điểm %, chưa đạt mục tiêu +10 điểm |
| Precision@10% | 55,0% | 40,0% | 11/20 hồ sơ queue là Y quan sát |
| Recall@20% | 44,9% | 24,5% | Dùng để xem trade-off khi tăng năng lực review |
| Brier score | 0,139 | N/A | Calibration trên dữ liệu nguồn |
| ECE, 10 bins | 0,095 | N/A | Chưa phải calibration production |

Bootstrap 95%: AP 0,458–0,691; ROC-AUC 0,753–0,889; Recall@10% 12,2%–28,6%; Precision@10% 30,0%–70,0%. Khoảng rộng do test chỉ có 49 Y.

KPI Recall@10% ≥60% không khả thi trên dataset prevalence 24,7%: queue 10% có trần lý thuyết khoảng `10/24,7 = 40,5%`. Muốn recall 60% thì queue tối thiểu đã khoảng 14,8% ngay cả với ranking hoàn hảo. KPI phải được chốt lại theo prevalence và review capacity thực tế.

### 8.2. Ảnh và chứng từ

| Module | Tập đánh giá | Kết quả v1 |
|---|---|---|
| YOLOv8s-seg | CarDD final test 419 ảnh/931 instance | Mask mAP50-95 0,5140; mask mAP50 0,6816 |
| DiT | RVL official validation sample 320 ảnh | Macro-F1 0,9283; balanced accuracy 0,9281 |
| PaddleOCR | SROIE validation 93 ảnh | CER 0,4097; WER 0,5592; 28,17 giây/trang |
| Rule KIE | SROIE validation 93 ảnh | Precision 0,8110; recall 0,5819; micro-F1 0,6776 |
| LayoutLMv3 | SROIE final test 361 ảnh | Field micro-F1 0,8659; Date F1 0,8320; Total F1 0,8995 |

Ba lớp CarDD yếu trên final test là `crack` 0,0863, `dent` 0,2779 và `scratch` 0,2804. Các metric public không chứng minh hiệu quả trên hồ sơ bảo hiểm Việt Nam.

### 8.3. Metric vận hành chưa thể kết luận

STP, False Hold và Net Value chưa có ground truth nghiệp vụ, chi phí được phê duyệt hoặc validation production nên chưa báo cáo như kết quả đạt. Prototype chỉ trình bày risk ranking và module status; người duyệt vẫn chịu trách nhiệm quyết định.

**Bằng chứng:** `reports/handoff/metrics_v1.md`, `reports/RESULTS.md`, `reports/CARDD_FINAL_TEST_V1.md`, `reports/DIT_INDEPENDENT_VALIDATION_V1.md`, `reports/LAYOUTLMV3_FINAL_TEST_V1.md`.

## 9. Risk Register v2

| ID | Rủi ro | Mức | Biện pháp hiện tại | Trạng thái |
|---|---|---|---|---|
| R14 | Phụ thuộc nhóm proxy nhân khẩu học/địa lý/sở thích/nghề nghiệp | Cao | Đánh giá policy trên `val_fs`, fairness review, không dùng hobbies làm lý do gian lận | Mở |
| R15 | Prevalence nguồn 24,7% khác production giả định 5–10% | Cao | Scenario rõ giả định; external/domain validation trước calibration | Mở |
| R16 | Provenance nhãn `fraud_reported` chưa xác minh | Cao | Xem nhãn là observed status; xây label contract và adjudication | Mở |
| R17 | Feature có thể chỉ xuất hiện sau intake | Cao | Data dictionary theo stage; feature gate theo scoring timestamp | Đang kiểm soát |
| R18 | Frozen test tabular đã dùng lại cho sensitivity | Trung bình | Dùng `train_fs/val_fs`; cần external test mới | Đã ghi nhận, chưa đóng |
| R19 | License/consent public data, đặc biệt CarDD | Cao | Lưu manifest/license; xin prior consent; không redistribute raw data | Mở |
| R20 | Các nguồn public không có `claim_id` chung | Cao | Đánh giá module riêng; golden claim synthetic chỉ kiểm luồng, không dùng chứng minh metric | Mở |
| R21 | Chỉ 247 Y, frozen test có 49 Y | Trung bình | Repeated CV, bootstrap CI, thu thập external set | Mở |
| R22 | Final test bị biến thành validation nếu chạy lặp | Cao | Checkpoint hash, execution lock, từ chối rerun | Đang kiểm soát |
| R23 | OCR sai/chậm | Cao | Error analysis trên 93 validation; thử deskew/resize/runtime trên validation | Mở |
| R24 | `crack`, `dent`, `scratch` còn yếu | Cao | Error gallery và dữ liệu đúng miền; không tối ưu theo final test | Mở |
| R25 | PII trong ảnh/chứng từ và API demo chưa có auth | Cao | Không log PII, giới hạn quyền, thêm authentication/authorization trước pilot | Mở |
| R26 | Detector ảnh AI/provenance tạo false certainty | Cao | Trả `inconclusive`; benchmark camera/edit/social/re-capture/AI theo nguồn; human review | Mở |
| R27 | Thiếu checkpoint trên máy demo làm pipeline `partial` | Trung bình | Model registry, SHA-256, readiness endpoint, không giả kết quả module | Mở |
| R28 | Domain shift sang bảo hiểm Việt Nam | Cao | Dataset có consent, taxonomy/ground truth mới, UAT và monitoring | Mở |

Không có rủi ro nào được xem là “đã giải quyết” chỉ vì code chạy. Pilot chỉ mở sau legal/PII, domain validation, security/load test, UAT, monitoring và rollback drill.

**Bằng chứng:** `reports/handoff/risk_register_v2_additions.md`, `reports/MEDIA_AUTHENTICITY_V2_AND_EVIDENCE_GATE.md`, `docs/handbook/08_DEFINITION_OF_DONE.md`.

## 10. Prompt/retrieval test set và hallucination/citation sơ bộ cho RAG/GenAI

### 10.1. Quyết định phạm vi

**N/A trong baseline hiện tại.** Hệ thống không dùng RAG, chatbot hay external LLM để tạo risk score, OCR/KIE hoặc quyết định claim. Vì vậy không có prompt/retrieval test result để báo cáo; ghi N/A là đúng hơn tạo một kết quả giả.

Reviewer UI chỉ hiển thị output có cấu trúc từ XGBoost, YOLO, DiT, PaddleOCR, LayoutLMv3, rules, NetworkX và media-authenticity. Điểm risk không được đổi thành câu “hồ sơ gian lận”, và model không tự từ chối hồ sơ.

### 10.2. Protocol nếu nhóm mở RAG sau Evaluation v1

Tập test tối thiểu nên có bốn nhóm: câu hỏi có đúng một nguồn hỗ trợ; câu hỏi cần tổng hợp nhiều nguồn; câu hỏi nguồn mâu thuẫn; câu hỏi không có đáp án. Mỗi mẫu lưu câu hỏi, answer key, document/page/region hợp lệ, mệnh đề bắt buộc và mệnh đề cấm suy diễn.

Các metric cần đo gồm retrieval Recall@K, citation precision/recall, groundedness theo từng mệnh đề, answer correctness và abstention accuracy. Hallucination được tính khi câu trả lời chứa mệnh đề không có nguồn hỗ trợ, thêm số/ngày/điều khoản không tồn tại hoặc biến tín hiệu model thành kết luận gian lận. Ngưỡng pass phải được khóa trước test; trường hợp không đủ nguồn phải trả “không đủ bằng chứng”.

### 10.3. Kết luận ghi vào báo cáo

> RAG/GenAI chưa thuộc phạm vi baseline của Evaluation v1 nên prompt/retrieval test set và hallucination/citation evaluation được ghi N/A. Core inference không gọi LLM bên ngoài. Nếu bổ sung trợ lý hỏi đáp policy/SOP, nhóm sẽ xây test set có citation ground truth theo document/page/region, đo retrieval, groundedness, citation correctness và khả năng từ chối trả lời khi không đủ bằng chứng trước khi tích hợp vào sản phẩm.

## 11. Kết luận chung cho các mục bổ sung

Nhóm đã có Data + Baseline + Evaluation v1 ở mức nghiên cứu: audit phát hiện và sửa leakage thật; các model chính đã có metric tách theo validation/final test; XGBoost được chọn làm risk-ranking model; YOLOv8s và LayoutLMv3 được khóa theo rule đặt trước. Prototype đã nối core risk, consistency, relationship, evidence và audit trail trên cùng `claim_id`.

Trạng thái phù hợp là **Conditional Go cho Technical PoC**. Chưa đủ căn cứ để go-live vì KPI tabular tương đối chưa đạt, OCR và một số lớp ảnh còn yếu, nhãn/domain/license còn hạn chế, máy tích hợp chưa có đủ checkpoint multimodal, và chưa hoàn tất security, dữ liệu Việt Nam, UAT, monitoring hay rollback.
