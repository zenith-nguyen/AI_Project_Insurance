# Triển khai nhánh chứng từ, consistency và NetworkX v1

**Ngày cập nhật:** 11/10/2026
**Mục tiêu sản phẩm:** trợ lý rà soát hồ sơ bồi thường xe, cung cấp bằng chứng và tín hiệu cho người thẩm định; không tự động từ chối hồ sơ.

## Trạng thái chính xác

| Thành phần | Đã xây trong source code | Đã kiểm thử cục bộ | Đã chạy metric trên dữ liệu thật |
|---|---:|---:|---:|
| Document classifier DiT | Adapter inference + notebook validation | Có, kiểm tra contract bằng mock | Smoke metric 0,9626 trên sample từ upstream train; independent validation chờ chạy |
| PaddleOCR | Adapter chuẩn hóa output v2/v3 + notebook CER/WER | Có | Có: CER 0,4097; WER 0,5592 trên 93 SROIE validation |
| Rule KIE | Trích xuất ngày, tổng tiền, số chứng từ, biển số | Có | Có: F1 0,6776 cho date/total trên validation |
| LayoutLMv3 KIE | Adapter checkpoint + notebook fine-tune | Có preflight | Chưa train |
| Consistency rules | Amount/date/plate với pass/fail/unknown | Có | Chưa có claim-document thật |
| NetworkX | Graph point-in-time và sáu feature v1 | Có | Chỉ demo synthetic; chưa có graph thật |
| Reviewer result contract | JSON hợp nhất damage/document/rules/graph/risk | Có | Chưa tích hợp API/UI |

Baseline document validation đã có metric thật. Không dùng từ “hoàn thành model chứng từ” trước khi LayoutLMv3 được train, so sánh và khóa. Không dùng kết quả synthetic NetworkX như bằng chứng phát hiện fraud.

## Source code đã tạo

- `src/document/schema.py`: hợp đồng `OCRToken`, `ExtractedField`, `DocumentResult`.
- `src/document/classifier.py`: adapter `DiTClassifier` cho `microsoft/dit-base-finetuned-rvlcdip`, pin revision `23f8b03...`.
- `src/document/ocr.py`: adapter `PaddleOCREngine`, chuẩn hóa output PaddleOCR cũ và mới.
- `src/document/kie.py`: rule KIE v1 và guard yêu cầu LayoutLMv3 checkpoint đã fine-tune.
- `src/document/metrics.py`: CER, WER và field micro precision/recall/F1.
- `src/document/pipeline.py`: orchestration classifier → OCR → KIE, có trace ID và model version.
- `src/integration/consistency.py`: kiểm tra số tiền, ngày và biển số; missing/low confidence trả `unknown`.
- `src/graph/claim_graph.py`: dựng graph tại thời điểm chấm điểm và tạo feature NetworkX.
- `src/integration/review.py`: hợp nhất tín hiệu thành payload reviewer; luôn yêu cầu human review.

Cấu hình được tách khỏi code tại `configs/document_pipeline.yaml`, `configs/consistency_rules.yaml`, `configs/graph_features.yaml`. Dependency tùy chọn nằm trong `requirements-document.txt`.

## Notebook và thứ tự chạy

1. Chạy lại `Document_SROIE_Processed_Split_Acc2_v1.ipynb` bản mới. Kết quả bắt buộc: train 525, validation 93, test 361 và cả ba cặp cross-split duplicate bằng 0.
2. Chạy `Document_Baselines_Acc2_v1.ipynb` trên GPU. Notebook đo:
   - DiT: macro-F1 và balanced accuracy trên 320 ảnh validation khóa từ RVL sample;
   - PaddleOCR: CER, WER và thời gian/trang trên 93 SROIE validation;
   - rule KIE: precision, recall và micro-F1 cho ngày và tổng tiền.

Notebook cài PaddlePaddle 3.2.0 từ index CPU chính thức để tránh lệch CUDA của Colab; phần DiT vẫn dùng GPU. Nếu runtime không có wheel PaddlePaddle tương thích, đổi Colab runtime sang Python được PaddlePaddle hỗ trợ rồi chạy lại từ đầu.

Quy tắc đã khóa trước khi xem kết quả LayoutLMv3: candidate chỉ được chọn nếu field exact-match micro-F1 cho `date`/`total` tăng ít nhất **0,02** so với rule isolated baseline và weak-alignment coverage đạt ít nhất **0,85**. Nếu không đạt, giữ rule baseline và ghi candidate là không được chọn.
3. Gửi file `reports/metrics/documents/document_baselines_validation_v1.json` để review. Test vẫn khóa.
4. Chạy `Document_DiT_Independent_Validation_Acc2_v1.ipynb` để thay smoke metric từ upstream train bằng metric trên upstream RVL validation.
5. Chạy `Document_LayoutLMv3_Candidate_Acc2_v1.ipynb`. Notebook fine-tune trên 525 train, chọn checkpoint theo field exact-match F1 trên 93 validation, ghi hash cây checkpoint và không đọc test.
6. Chỉ đặt quy tắc chọn model và duyệt validation xong mới tạo notebook final test riêng.
7. `Claim_Consistency_NetworkX_Demo_Acc2_v1.ipynb` chạy CPU được. Đây là demo logic; benchmark graph thật chỉ mở khi có bảng claim/entity/edge hợp lệ.

## Model nào đang chạy việc gì

Sản phẩm không phải một model duy nhất:

1. **YOLOv8s-seg** là model ảnh tổn thất đã train và final-test thật.
2. **DiT** là baseline pretrained để phân loại loại chứng từ. Vòng đầu chỉ inference; nhóm chưa fine-tune DiT.
3. **PaddleOCR** là OCR engine pretrained, trả text, confidence và tọa độ; vòng đầu chưa fine-tune.
4. **Rule KIE v1** là thuật toán deterministic sau OCR. **LayoutLMv3** là candidate học máy cần fine-tune và so sánh trên cùng validation.
5. **Consistency rules** là luật nghiệp vụ có giải thích, không phải model học máy.
6. **NetworkX** là thư viện dựng graph và tính feature, không phải model. Feature graph có thể đưa vào XGBoost/risk model sau khi có dữ liệu claim thật.
7. **XGBoost tabular** hiện là baseline nghiên cứu để xếp hạng rủi ro, chưa đạt KPI và chưa production-ready.

## Codex và Colab chia việc thế nào

Codex thực hiện source code, cấu hình, notebook builder, unit test, report, API contract và đóng gói. Colab chỉ cần cho các bước phụ thuộc Google Drive, GPU, tải model lớn hoặc benchmark lâu. Source code sau khi checkpoint được khóa sẽ dùng lại trong API/UI; notebook không phải sản phẩm cuối.

## Dòng xử lý sản phẩm

```text
claim_id + ảnh xe + chứng từ
  ├─ YOLOv8s-seg → vùng và loại hư hỏng
  ├─ DiT → loại chứng từ
  │    └─ PaddleOCR → text + bbox
  │         └─ Rule KIE/LayoutLMv3 → trường chuẩn hóa + evidence
  ├─ Consistency rules → pass/fail/unknown
  ├─ NetworkX → shared-entity/connected-component/risk-distance features
  └─ XGBoost/rules → mức ưu tiên rà soát
                         ↓
                reviewer UI + audit trail
```

Mọi nhánh chỉ hợp nhất bằng `claim_id` thật. Tất cả node/edge/field phải có thời điểm sẵn có không muộn hơn thời điểm scoring. Dataset công khai không được ghép theo từng dòng để tạo một claim giả.

## Bằng chứng kiểm thử hiện tại

- Toàn bộ suite: **51 passed, 1 skipped**.
- Notebook JSON: hợp lệ.
- Tất cả code cell trong ba notebook mới: compile PASS.
- Phần chưa có bằng chứng: LayoutLMv3 checkpoint, graph metric trên dữ liệu nghiệp vụ thật, API/UI/UAT.

## Các giới hạn phải trình bày

- RVL sample có thể thuộc cùng nguồn upstream dùng để fine-tune DiT, nên metric chỉ là kiểm tra kỹ thuật, chưa chứng minh generalization cho hồ sơ bảo hiểm Việt Nam.
- SROIE là receipt tiếng Anh; không đại diện cho toàn bộ chứng từ bảo hiểm Việt Nam.
- LayoutLMv3 notebook tạo BIO labels bằng weak alignment từ entity string sang OCR words; cần đo tỷ lệ alignment và review mẫu lỗi.
- Consistency và NetworkX cần dữ liệu claim thật có khóa và timestamp. Hiện mới chứng minh thuật toán bằng test/synthetic demo.
- Public data và model có license khác nhau; production vẫn khóa tới khi legal/PII review hoàn tất.
