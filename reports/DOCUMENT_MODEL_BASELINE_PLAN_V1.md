# Document Model Baseline Plan v1

## Kết luận hiện tại

Nhánh CarDD đã hoàn tất model segmentation: `YOLOv8s-seg` là model được chọn sau khi tăng validation mask mAP50-95 từ 0.5175 lên 0.5284 và đã được đánh giá final test đúng một lần. Nhánh chứng từ chưa có model cuối cùng, nhưng data gate SROIE đã PASS và baseline validation đã hoàn tất: DiT macro-F1 0,9626, PaddleOCR CER 0,4097/WER 0,5592 và rule KIE F1 0,6776. LayoutLMv3 candidate chờ train và so sánh.

Nhánh chứng từ là một pipeline gồm ba bài toán, không phải một model duy nhất:

1. **Document classification** xác định loại tài liệu trước khi OCR. Baseline đề xuất là checkpoint pretrained [`microsoft/dit-base-finetuned-rvlcdip`](https://huggingface.co/microsoft/dit-base-finetuned-rvlcdip), đã được fine-tune trên RVL-CDIP 16 lớp. Bước đầu chỉ benchmark inference trên sample RVL-CDIP đã khóa; chưa train lại.
2. **OCR** chuyển ảnh thành chữ và tọa độ. Baseline đề xuất là [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) pretrained. Đo CER, WER và exact match trên ground truth của từng bộ dữ liệu; chưa fine-tune ở vòng đầu.
3. **Key Information Extraction (KIE)** trích xuất trường như số hóa đơn, ngày, tổng tiền, bên phát hành. Candidate nghiên cứu là [`microsoft/layoutlmv3-base`](https://huggingface.co/microsoft/layoutlmv3-base), fine-tune riêng theo schema đã chuẩn hóa từ CORD, SROIE, FUNSD và XFUND. Checkpoint này có ràng buộc giấy phép CC BY-NC-SA 4.0 nên chỉ dùng nghiên cứu cho tới khi legal review hoàn tất.

## Baseline nghĩa là gì

Baseline là mốc đơn giản, tái lập được để chứng minh model/candidate sau có thật sự tốt hơn. Baseline không đồng nghĩa model cuối cùng và không phải tự đặt ra bằng cảm tính.

| Bài toán | Baseline | Nguồn | Metric chính |
|---|---|---|---|
| Phân loại chứng từ | DiT pretrained/fine-tuned RVL-CDIP, không fine-tune thêm ở vòng đầu | Model card và revision được pin | Macro-F1; balanced accuracy |
| OCR | PaddleOCR pretrained | Release/version được pin | CER; WER; field exact match |
| KIE | Rule-based sau OCR, sau đó LayoutLMv3 candidate | Code, config, checkpoint hash | Entity/field micro-F1 và macro-F1 |

## Dữ liệu dùng ở đâu

- RVL-CDIP sample: benchmark phân loại 16 loại tài liệu, không đại diện trực tiếp cho hồ sơ bảo hiểm Việt Nam.
- CORD và SROIE: receipt OCR/KIE. SROIE phải dùng processed split đã loại 8 ảnh train trùng test.
- FUNSD: form understanding và quan hệ key-value.
- XFUND: đánh giá transfer đa ngôn ngữ; không có tiếng Việt nên không được dùng để tuyên bố chất lượng tiếng Việt.
- MIDV: nhánh giấy tờ định danh, hiện hoãn; không cần tải full để chạy baseline receipt/form.

## Quy trình chứng minh

1. Pin nguồn, revision và checksum của dataset/model.
2. Audit ảnh hỏng, số lượng, exact duplicate và near duplicate trước khi tạo split.
3. Khóa train/validation/test và seed. Test không tham gia chọn model.
4. Chạy baseline với config, package version và hardware được ghi lại.
5. Chạy candidate trên cùng split và cùng metric.
6. Chọn candidate theo quy tắc đặt trước, không đổi ngưỡng sau khi xem test.
7. Chạy final test đúng một lần; lưu report, confusion matrix, error analysis và SHA-256 checkpoint.
8. Tạo model card nêu dữ liệu, giới hạn, license, nhóm lỗi và điều kiện không được dùng.

## Trạng thái cổng

- Cấu trúc raw data: đã qua registry/manifest preflight.
- SROIE raw split: phát hiện 8 cặp exact duplicate train/test; processed split đã loại đúng tám mẫu và cả ba cross-split overlap bằng 0.
- Benchmark document: validation baseline đã hoàn tất; test vẫn khóa trong thời gian train/chọn LayoutLMv3.
- Production: khóa cho tới khi có dữ liệu chứng từ bảo hiểm thật, review PII/license và kiểm thử end-to-end.
