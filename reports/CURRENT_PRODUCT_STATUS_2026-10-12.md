# Trạng thái sản phẩm bảo hiểm AI — 12/10/2026

## Sản phẩm đang xây là gì?

Đây là **hệ thống hỗ trợ tiếp nhận và rà soát hồ sơ bồi thường**, không phải hệ thống tự động kết luận gian lận hoặc tự động từ chối claim.

Đầu vào dự kiến:

1. dữ liệu claim dạng bảng;
2. ảnh hư hỏng xe;
3. hóa đơn, form và chứng từ;
4. quan hệ giữa claim, khách hàng, xe, tài khoản, điện thoại, địa chỉ và đơn vị sửa chữa.

Đầu ra dự kiến:

- vùng và loại hư hỏng trên ảnh;
- loại chứng từ, text OCR, ngày và tổng tiền;
- cờ không nhất quán giữa claim và chứng từ;
- đặc trưng quan hệ và điểm ưu tiên review;
- evidence, confidence, model version và audit trail cho reviewer.

## Trạng thái theo module

| Module | Trạng thái | Bằng chứng hiện có | Còn thiếu để dùng trong MVP |
|---|---|---|---|
| Tabular fraud risk | Baseline nghiên cứu hoàn tất | XGBoost có metric và calibration | KPI Recall@10% chưa đạt; label provenance yếu; cần dữ liệu nghiệp vụ |
| Damage image | Model public-data đã khóa | YOLOv8s-seg final test mask mAP50-95 0,5140 | Consent CarDD; cải thiện `crack`, `dent`, `scratch`; domain validation |
| Document classification | Independent validation hoàn tất | DiT macro-F1 0,9283; balanced accuracy 0,9281 | Validation trên chứng từ bảo hiểm Việt Nam |
| OCR | Baseline hoàn tất | PaddleOCR CER 0,4097; WER 0,5592 | Chất lượng và latency chưa đạt mức sản phẩm |
| KIE | Candidate được chọn trên validation | LayoutLMv3 F1 0,9214 so với rule 0,6834 | Final test vẫn khóa; mới có `date` và `total`; cần domain data |
| Consistency | Engineering demo PASS | Rule amount/date/plate và schema output | Benchmark trên claim thật; policy nghiệp vụ được duyệt |
| NetworkX | Point-in-time demo PASS | Bốn graph feature demo đã chạy | Claim/entity/edge thật, timestamp, outcome và graph evaluation |
| Inference API | Chưa đóng gói | Có module Python độc lập notebook | Registry checkpoint, service orchestration, FastAPI, auth, limits |
| UI/MVP | Chưa xây | Có workflow và output contract | Upload, reviewer screen, corrections, audit trail |
| Deployment/UAT | Chưa bắt đầu | Có roadmap | Docker, staging, golden set, security/load test, pilot và rollback |

## Trạng thái theo cổng sản phẩm

| Gate | Trạng thái |
|---|---|
| G0 — Public data intake/registry | Hoàn tất trong scope báo cáo |
| G1 — Audit, leakage, data dictionary | Hoàn tất trong scope báo cáo |
| G2 — Module baselines và validation | Hoàn tất cho bản nghiên cứu v1 |
| G3 — Dữ liệu bảo hiểm thật và ground truth | Chưa có |
| G4 — Graph/risk evaluation trên dữ liệu thật | Mới có demo kỹ thuật |
| G5 — Model registry, inference API, Docker | Chưa hoàn tất |
| G6 — UI/MVP | Chưa bắt đầu triển khai |
| G7 — End-to-end/UAT/security/load test | Chưa bắt đầu |
| G8 — Go-live có kiểm soát | Chưa sẵn sàng |

Vì vậy, dự án **đã đủ mạnh cho Báo cáo tiến độ lần 2 và một technical PoC theo module**. Dự án **chưa phải MVP end-to-end và chưa production-ready**.

## Thứ tự công việc tiếp theo

1. Đóng gói evidence hiện tại và trình bày Báo cáo tiến độ 2.
2. Review selection report và checkpoint hash của LayoutLMv3; sau đó tạo protocol final test một lần trên 361 SROIE test.
3. Đăng ký các checkpoint đã chọn bằng model name, revision, SHA-256, input/output schema và metric.
4. Tạo inference service chạy độc lập notebook: tabular score, CarDD segmentation, DiT → OCR → LayoutLMv3, consistency và graph features.
5. Tạo FastAPI contract và UI reviewer tối thiểu.
6. Tạo golden end-to-end set với `claim_id`; public datasets không được ghép giả theo từng dòng.
7. Thu thập dữ liệu bảo hiểm Việt Nam có consent, PII policy và ground-truth protocol.
8. Chạy domain validation, security/load test và UAT trước pilot.

## Việc không cần làm lại

- Không chạy lại CarDD final test.
- Không dùng lại DiT smoke metric 0,9626 làm metric chính; dùng independent macro-F1 0,9283.
- Không train lại LayoutLMv3 chỉ vì epoch 5 thấp hơn epoch 4; Trainer đã giữ best checkpoint epoch 4.
- Không ghép CarDD, SROIE, RVL-CDIP và tabular Kaggle theo từng dòng khi không có `claim_id` thật.
- Không gọi NetworkX demo là fraud detection model.
