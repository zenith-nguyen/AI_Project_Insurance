# Lộ trình thêm chứng từ và network/NetworkX

## Nguyên tắc

Mỗi nhánh được xây dựng và đánh giá độc lập trước. Chỉ ghép tín hiệu khi các nguồn có `claim_id` chung hoặc một khóa liên kết hợp lệ. Không ghép CarDD, CORD và Kaggle theo dòng vì đây là các bộ dữ liệu khác nhau.

## Kiến trúc dự kiến

```text
Hồ sơ tabular ──> tabular risk score ──┐
Ảnh tổn thất ───> damage signals ──────┤
Chứng từ ───────> extracted fields ────┼──> claim-level feature table ──> calibrated risk model
Network/graph ──> graph risk features ─┘
```

### Nhánh chứng từ

Đầu vào tối thiểu: `claim_id`, `document_id`, loại chứng từ, thời điểm nhận, ảnh/PDF và quyền sử dụng. OCR/document model trước hết chỉ trích xuất trường và độ tin cậy. Các tín hiệu như số tiền không khớp, ngày không hợp lệ hoặc thông tin người nhận khác hồ sơ chỉ được tạo khi có claim thật để đối chiếu.

CORD/SROIE/FUNSD/XFUND có thể dùng để học hoặc benchmark OCR/extraction độc lập nếu license phù hợp. Chúng không thể tự cung cấp nhãn fraud cho claim Kaggle.

### Nhánh NetworkX

Graph cần entity thật có liên kết: người được bảo hiểm, số điện thoại, địa chỉ, xe, tài khoản thanh toán, gara, đại lý và claim. Mỗi edge cần `event_time` để graph feature của một claim chỉ dùng thông tin đã tồn tại trước thời điểm chấm điểm.

Feature v1 nên đơn giản và giải thích được: số claim dùng chung entity, degree, số láng giềng, component size, số chu trình ngắn, PageRank và khoảng cách tới claim fraud đã xác nhận trong quá khứ. Không đưa label tương lai hoặc toàn bộ graph sau thời điểm claim vào feature.

### Ghép mô hình

Ưu tiên late fusion: mỗi module tạo một bảng signal ở mức `claim_id`, sau đó join vào Gold claim-level và huấn luyện/calibrate một model tổng. Cách này cho phép thiếu ảnh/chứng từ, audit từng nguồn và thay module mà không phải huấn luyện lại toàn bộ hệ thống từ đầu.

## Data contract cần có

| Nhánh | Khóa bắt buộc | Output tối thiểu |
|---|---|---|
| Tabular | `claim_id`, scoring time | calibrated risk score, explanation |
| Ảnh | `claim_id`, `image_id` | damage classes, mask area, confidence |
| Chứng từ | `claim_id`, `document_id` | extracted fields, OCR confidence, consistency flags |
| Graph | `claim_id`, entity IDs, event time | graph features và thời điểm cutoff |

## Thứ tự triển khai

1. Hoàn thành baseline CarDD độc lập.
2. Nhận sample chứng từ có quyền dùng, lập schema và benchmark OCR/extraction.
3. Nhận bảng entity-edge thật, xây graph snapshot theo thời gian và feature bằng NetworkX.
4. Tạo claim-level feature table có lineage.
5. Chọn model fusion chỉ trên train/validation; dùng external test mới cho đánh giá cuối.
