# Document EDA and Source Analysis v1

## Quy mô đã audit

| Dataset | Quy mô dùng hiện tại | Vai trò |
|---|---:|---|
| CORD v2 | 1.000 receipt images | OCR và receipt KIE |
| FUNSD | 199 form images | Form understanding, entity/relation extraction |
| XFUND | 1.393 images, bảy ngôn ngữ | Multilingual form transfer |
| SROIE | 987 rows trước remediation | Receipt OCR/KIE |
| RVL-CDIP | Sample 1.600 ảnh, 16 lớp | Document classification baseline |
| MIDV | Metadata only | ID-document branch, deferred |

## Quan sát nguồn

- CORD tập trung hóa đơn cửa hàng/nhà hàng Indonesia; phù hợp receipt KIE nhưng không đại diện claim form bảo hiểm.
- SROIE có receipt tiếng Anh và trường thông tin hữu ích, nhưng corrected mirror chứa exact train/test leakage nên không được dùng nguyên split.
- FUNSD nhỏ, biểu mẫu scan và quan hệ semantic; phù hợp thử KIE nhưng độ phủ layout thấp.
- XFUND hỗ trợ bảy ngôn ngữ nhưng không có tiếng Việt; chỉ dùng kiểm tra transfer, không dùng tuyên bố chất lượng tiếng Việt.
- RVL-CDIP sample cân bằng giúp benchmark classifier nhanh, nhưng taxonomy 16 lớp chung không phải taxonomy nghiệp vụ bảo hiểm.
- MIDV có dung lượng lớn và scope khác receipt/form; hoãn giúp giảm chi phí lưu trữ và tránh tải dữ liệu chưa dùng.

## Rủi ro phân phối dữ liệu

- Domain shift từ public documents sang ảnh điện thoại của người dùng Việt Nam.
- Khác ngôn ngữ, font, tiền tệ, định dạng ngày và chất lượng camera.
- Public data thiếu `claim_id`, policy context và nhãn fraud.
- Class balance nhân tạo của RVL sample không phản ánh traffic production.
- PII và license giới hạn khả năng dùng trực tiếp cho sản phẩm thương mại.

## Hệ quả với thí nghiệm

- Báo metric riêng theo dataset và task, không gộp tất cả thành một điểm duy nhất.
- Dùng public data để xây baseline kỹ thuật và kiểm tra pipeline.
- Cần pilot set chứng từ bảo hiểm Việt Nam có consent, PII controls và annotation guideline trước go-live.
- Khi chia dữ liệu thật, group theo `claim_id` để tránh cùng hồ sơ xuất hiện ở nhiều split.
