# Báo cáo tiến độ lần 2 — Bản tổng hợp dễ đọc

**Ngày cập nhật:** 12/10/2026  
**Trọng tâm:** Data + Baseline + Evaluation v1

## 1. Kết quả chính

Dự án đã hoàn thành data audit và baseline/evaluation v1 cho ba nhánh: dữ liệu bảng, ảnh hư hỏng xe và chứng từ. Nhóm cũng đã có demo consistency rules và NetworkX theo nguyên tắc point-in-time. Kết quả hiện đủ để chứng minh tính khả thi kỹ thuật, nhưng chưa đại diện cho hiệu quả trên dữ liệu bảo hiểm Việt Nam thực tế.

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

### 4.1. Ảnh hư hỏng xe

YOLOv8n-seg được dùng làm baseline. YOLOv8s-seg tăng validation mask mAP50-95 từ 0,5175 lên 0,5284, đạt quy tắc tăng tối thiểu 0,01 đã đặt trước. Checkpoint được khóa bằng SHA-256 trước khi mở test.

Final test chạy đúng một lần trên 419 ảnh/931 đối tượng và đạt mask mAP50-95 0,5140. Các lớp mạnh là `glass shatter` và `tire flat`; các lớp cần cải thiện là `crack`, `dent` và `scratch`.

### 4.2. Phân loại chứng từ

DiT đạt macro-F1 0,9283 và balanced accuracy 0,9281 trên 320 ảnh validation độc lập, cân bằng 20 ảnh cho mỗi lớp. Đây là metric chính để báo cáo; kết quả smoke 0,9626 không được dùng làm metric độc lập.

### 4.3. OCR

PaddleOCR đã xử lý 93 receipt validation, đạt CER 0,4097, WER 0,5592 và thời gian trung bình 28,17 giây/trang trong lần chạy baseline. Pipeline chạy được nhưng chất lượng và latency còn yếu.

### 4.4. Trích xuất thông tin

Rule KIE là baseline có thể giải thích, đạt field micro-F1 khoảng 0,6834 trong phép so sánh cô lập. LayoutLMv3 đạt 0,9214 trên validation cho hai trường `date` và `total`, vượt ngưỡng lựa chọn đặt trước. Candidate đã được chọn; SROIE test 361 ảnh vẫn khóa.

### 4.5. Consistency và NetworkX

Consistency rules và NetworkX point-in-time demo đều PASS. Đây là kiểm tra engineering trên dữ liệu synthetic, chứng minh thuật toán và output contract chạy đúng. Chưa có đủ claim/entity/edge thật để đo fraud lift.

## 5. Kiến trúc sản phẩm đã thống nhất

Sản phẩm là một reviewer console gồm bốn màn hình trong cùng ứng dụng:

1. **Claim Workbench:** xử lý hồ sơ hằng ngày.
2. **Evidence & Audit:** xem nguồn gốc và lịch sử của từng kết quả.
3. **Relationship Watch:** xem NetworkX và shared entities.
4. **Model Registry:** xem model version, checkpoint và metric.

UI dùng fixture JSON trong giai đoạn prototype và chuyển sang FastAPI khi inference service hoàn thành. Model chỉ đưa ra evidence và đề xuất route; người duyệt giữ quyền quyết định.

## 6. Giới hạn cần trình bày trung thực

- Public datasets chưa đại diện đầy đủ cho bảo hiểm xe tại Việt Nam.
- OCR còn yếu và KIE hiện mới đánh giá hai field.
- CarDD còn ba lớp yếu và cần bằng chứng quyền sử dụng phù hợp.
- `fraud_reported` là observed label có provenance chưa được xác minh đầy đủ.
- NetworkX hiện mới là demo logic, chưa phải fraud model.
- Chưa có model registry, inference API, security/load test và UAT hoàn chỉnh.

## 7. Kế hoạch giai đoạn kế tiếp

1. Review checkpoint/report rồi chạy LayoutLMv3 final test đúng một lần.
2. Đăng ký tất cả model và schema trong model registry.
3. Đóng gói inference bằng FastAPI.
4. Nối prototype hợp nhất với fixture rồi với live API.
5. Tạo golden set end-to-end theo `claim_id`.
6. Cải thiện OCR và các lớp CarDD yếu bằng error analysis trên train/validation hoặc dữ liệu miền mới.
7. Thu thập dữ liệu nghiệp vụ có consent, PII policy và quy trình xác lập ground truth.

## 8. Kết luận

Dự án đã vượt khỏi giai đoạn ý tưởng và đã có các module AI chạy được, metric, audit và bằng chứng lựa chọn model. Mốc tiếp theo là biến các module này thành một prototype end-to-end có API, UI, model registry và human review workflow. Production/go-live chỉ được xem xét sau domain validation, security/load test và UAT.

## 9. Nơi kiểm tra bằng chứng kỹ thuật

Nếu cần kiểm tra sâu hơn, không cần đọc toàn bộ thư mục `reports`. Chỉ mở các file sau:

- `CARDD_FINAL_TEST_V1.md`: final test ảnh xe và metric từng lớp.
- `DIT_INDEPENDENT_VALIDATION_V1.md`: validation độc lập của document classifier.
- `DOCUMENT_BASELINE_VALIDATION_V1.md`: OCR và rule KIE baseline.
- `LAYOUTLMV3_CANDIDATE_VALIDATION_V2.md`: kết quả lựa chọn KIE candidate.
- `DATA_LEAKAGE_CHECK_V1.md`: leakage và cách khắc phục.
- `CLAIM_CONSISTENCY_NETWORKX_DEMO_V1.md`: consistency/graph demo.
- `LAYER_B_STAGE_RELIABILITY_DICTIONARY_V1.md`: dictionary 39 trường theo stage.
