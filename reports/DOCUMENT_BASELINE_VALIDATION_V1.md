# Document Baseline Validation v1

**Ngày chạy:** 11/10/2026

**Split:** validation

**Final test:** vẫn khóa
**Report gốc trên Drive:** `/content/drive/MyDrive/AI_Project_Insurance_Acc 2/reports/metrics/documents/document_baselines_validation_v1.json`

## Data gate

SROIE processed split đã PASS: 525 train, 93 validation, 361 test; cả ba cặp exact cross-split overlap đều bằng 0. Test không tham gia split hoặc lựa chọn model.

## Kết quả baseline

| Task | Baseline | Dữ liệu validation | Metric |
|---|---|---:|---|
| Document classification | DiT RVL-CDIP revision `23f8b03...` | 320 ảnh, 20 ảnh × 16 lớp | Macro-F1 **0,9626**; balanced accuracy **0,9625** |
| OCR | PaddleOCR | 93 SROIE receipt | CER **0,4097**; WER **0,5592**; **28,17 giây/trang** |
| KIE | Rule KIE v1 | 93 SROIE receipt | Precision **0,8110**; recall **0,5819**; micro-F1 **0,6776** |

KIE v1 mới đánh giá hai field `document_date` và `total_amount`.

## Diễn giải

**DiT:** kết quả cao và đủ dùng làm smoke benchmark kỹ thuật cho 16 lớp RVL-CDIP. Sample intake này được lấy từ upstream `train`, là nguồn đã dùng để fine-tune DiT, nên 0,9626 không phải independent validation. Notebook `Document_DiT_Independent_Validation_Acc2_v1.ipynb` đã được tạo để đo lại trên upstream `validation`. Cả hai vẫn chưa chứng minh chất lượng trên repair estimate, police report hay Vietnamese ID.

**PaddleOCR:** baseline chạy thành công nhưng CER/WER còn cao và latency CPU rất lớn. Các cảnh báo resize ảnh 4961×7016 xuống giới hạn 4000 là hành vi xử lý ảnh, không phải run failure. Cần so sánh pipeline OCR nhẹ hơn, tiền xử lý deskew/resize và GPU/runtime phù hợp trên cùng 93 validation.

**Rule KIE:** precision tương đối tốt nhưng recall thấp; rule bỏ sót nhiều trường. Kết quả này phù hợp vai trò baseline có giải thích để LayoutLMv3 candidate phải vượt qua.

## Quyết định sau validation

1. Giữ DiT pretrained làm document-classification baseline kỹ thuật; chạy thêm official RVL validation trước khi báo cáo metric độc lập.
2. Giữ PaddleOCR làm OCR baseline v1, đồng thời tạo backlog tối ưu latency và chất lượng.
3. Khóa Rule KIE v1 ở F1 0,6776 làm mốc so sánh.
4. Chạy LayoutLMv3 candidate trên 525 train/93 validation. Candidate chỉ được xem xét nếu cải thiện KIE F1 và có error analysis theo field.
5. Không dùng 361 SROIE test trước khi quy tắc chọn candidate được khóa.
