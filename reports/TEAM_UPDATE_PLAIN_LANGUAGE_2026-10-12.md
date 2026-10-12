# Cập nhật dự án cho cả nhóm — 12/10/2026

## Dự án đang làm sản phẩm gì?

Nhóm đang xây dựng **Insurance Review Console**: một công cụ hỗ trợ nhân viên bảo hiểm tiếp nhận và rà soát hồ sơ bồi thường xe.

Hệ thống nhận bốn nhóm thông tin:

1. thông tin khai báo của hồ sơ;
2. ảnh hư hỏng xe;
3. hóa đơn, biên bản và giấy tờ;
4. mối quan hệ giữa claim, khách hàng, xe và đơn vị sửa chữa.

Hệ thống trả về vùng hư hỏng, nội dung trích xuất từ chứng từ, các điểm không nhất quán và hồ sơ cần ưu tiên xem xét. **Hệ thống không tự kết luận gian lận và không tự từ chối bồi thường.** Quyết định cuối cùng vẫn thuộc về người duyệt.

## Những phần đã hoàn thành

| Phần việc | Kết quả dễ hiểu | Trạng thái |
| --- | --- | --- |
| Quản lý dữ liệu | Đã lập danh mục nguồn, kiểm tra file hỏng, bản trùng và rò rỉ giữa các tập dữ liệu | Hoàn thành cho phạm vi báo cáo |
| Ảnh hư hỏng xe | Đã chọn YOLOv8s, khóa checkpoint và chạy final test đúng một lần | Hoàn thành bản nghiên cứu v1 |
| Phân loại chứng từ | DiT đạt macro-F1 0,9283 trên tập validation độc lập 320 ảnh | Hoàn thành validation v1 |
| Đọc chữ | PaddleOCR đã chạy đủ baseline; CER 0,4097 và WER 0,5592 | Chạy được nhưng cần cải thiện |
| Trích xuất ngày và tổng tiền | LayoutLMv3 đạt validation F1 0,9214, cao hơn rule baseline 0,6834 | Đã chọn candidate; chưa mở final test |
| Kiểm tra nhất quán | Đã có rule so sánh số tiền, ngày và biển số | Demo kỹ thuật PASS |
| Quan hệ NetworkX | Đã tính được degree, shared entity, component và two-hop claim theo point-in-time | Demo kỹ thuật PASS |
| Giao diện | Hợp nhất xử lý claim, evidence/audit và relationship view | Prototype v2 có hướng dẫn thao tác đã có |

## Chúng ta đang dùng model và công nghệ nào?

Dự án không phải một model duy nhất. Đây là một chuỗi module, mỗi module xử lý một loại bằng chứng:

| Nhu cầu | Công nghệ/model hiện tại | Đầu ra cho sản phẩm |
| --- | --- | --- |
| Xếp hạng rủi ro từ dữ liệu hồ sơ | XGBoost, so với Logistic Regression/Random Forest/LightGBM | Điểm ưu tiên và explanation; không phải kết luận fraud |
| Nhận diện vùng hư hỏng | YOLOv8s-seg | Mask và loại hư hỏng trên ảnh xe |
| Nhận biết loại chứng từ | Microsoft DiT fine-tuned RVL-CDIP | Invoice, form, letter, ID-like và các loại tài liệu khác |
| Đọc chữ | PaddleOCR | Text và vị trí chữ trên trang |
| Trích xuất trường | LayoutLMv3 token classification | Ngày và tổng tiền; sẽ mở rộng khi có nhãn nghiệp vụ |
| Đối chiếu dữ liệu | Python consistency rules | Cờ lệch số tiền, ngày, biển số và trường bắt buộc |
| Phân tích quan hệ | NetworkX | Shared entity, degree, component và two-hop claims |
| Cung cấp cho UI | FastAPI theo kế hoạch | Một response thống nhất theo `claim_id` |

XGBoost là model tổng hợp hiện tại cho nhánh tabular. Các tín hiệu ảnh, chứng từ và graph chưa được phép ghép giả theo từng dòng vì public datasets không có `claim_id` chung. Khi có dữ liệu liên kết thật, output của các module mới trở thành feature/evidence cho bước xếp hạng tổng hợp.

## Kết quả XGBoost cần nói đúng

Trong cross-validation dùng để chọn model, XGBoost đạt AP 0,706 và Recall@10% 30,3%. Sau khi chọn, kết quả frozen test là AP 0,559 và Recall@10% 22,4%; rule baseline đạt 16,3%. Vì vậy model tăng 6,1 điểm phần trăm so với rule nhưng chưa đạt mục tiêu tương đối +10 điểm.

Không dùng KPI tuyệt đối Recall@10% ≥ 60% trên dataset prevalence 24,7%, vì trần toán học chỉ khoảng 40,5%. KPI phải được xác nhận lại theo prevalence và review capacity thực tế.

## Các phát hiện quan trọng

- Audit phát hiện tám ảnh SROIE trùng giữa train và test. Nhóm giữ nguyên test, loại bản train trùng và chia lại train/validation theo nhóm SHA-256. Split mới 525/93/361 không còn trùng chéo.
- FUNSD từng bị đếm thành 398 mẫu vì lưu hai bản giống nhau. Dataset chuẩn thực tế có 199 mẫu.
- YOLOv8s tốt ở `glass shatter` và `tire flat`, nhưng còn yếu ở `crack`, `dent` và `scratch`.
- OCR đang là điểm nghẽn chính của nhánh chứng từ.
- Dataset bảng chỉ phù hợp để dựng baseline. Nhãn `fraud_reported` chưa có bằng chứng đầy đủ rằng mọi trường hợp đã được điều tra và xác nhận.

## Số liệu nên dùng khi trình bày

- CarDD final test: mask mAP50-95 **0,5140** trên 419 ảnh và 931 đối tượng.
- DiT independent validation: macro-F1 **0,9283**.
- PaddleOCR validation: CER **0,4097**, WER **0,5592**.
- LayoutLMv3 validation: field micro-F1 **0,9214**; rule baseline **0,6834**.
- Consistency và NetworkX: demo code **PASS**, chưa phải metric phát hiện gian lận trên dữ liệu thật.

## Sản phẩm hiện đang ở đâu?

Hiện tại dự án là **technical PoC theo từng module** và đã đủ bằng chứng cho Báo cáo tiến độ lần 2. Dự án chưa phải MVP end-to-end và chưa sẵn sàng go-live.

Các model đã chạy được riêng lẻ. Bước tiếp theo là khóa final test của LayoutLMv3, đăng ký model, đóng gói API, nối prototype UI và tạo một bộ hồ sơ mẫu có chung `claim_id` để kiểm thử toàn bộ luồng.

## Việc tiếp theo đã thống nhất

1. Chạy LayoutLMv3 final test đúng một lần bằng checkpoint đã chọn.
2. Tạo model registry chứa tên, phiên bản, SHA-256, metric và input/output schema.
3. Đóng gói FastAPI với `/health`, `/version` và `/claims/{claim_id}/analyze`.
4. Nối UI hợp nhất với fixture JSON trước, sau đó thay bằng live API.
5. Cải thiện OCR và phân tích lỗi ba lớp ảnh yếu trên train/validation hoặc dữ liệu miền mới; không chỉnh model theo final test.
6. Tạo golden set end-to-end có `claim_id`, evidence và expected outputs.
7. Thu thập dữ liệu nghiệp vụ có consent, PII policy và ground-truth protocol trước pilot.

## Những việc cần team hỗ trợ

- Nhóm prototype: dùng file `prototype/insurance_review_console_unified.html` làm định hướng màn hình.
- Nhóm nghiệp vụ: xác nhận trường nào có ở intake, sau giám định và khi đủ chứng từ.
- Nhóm dữ liệu: chuẩn bị một số hồ sơ giả lập hoặc đã ẩn danh có cùng `claim_id` xuyên suốt ảnh, chứng từ và dữ liệu bảng.
- Nhóm báo cáo: dùng số liệu trong tài liệu này; không dùng lại metric DiT smoke 0,9626 làm kết quả chính.
- Người phụ trách pháp lý/dữ liệu: bổ sung bằng chứng quyền sử dụng CarDD và đánh giá license/PII cho dữ liệu chứng từ.

## Câu kết luận ngắn để báo cáo

> Nhóm đã hoàn thành data audit, baseline và validation v1 cho các nhánh ảnh xe, chứng từ và dữ liệu bảng; đồng thời chứng minh được consistency rules và graph features có thể chạy. Giai đoạn tiếp theo chuyển từ các module nghiên cứu sang một prototype end-to-end có model registry, API, giao diện reviewer và human-in-the-loop.
