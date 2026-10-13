# Media authenticity v2 và quy tắc khi hồ sơ thiếu dữ liệu

## Người dùng có phải gọi endpoint authenticity riêng không?

Không. Khi người dùng tải ảnh lên, hệ thống tự chạy kiểm tra nguồn gốc và lưu kết quả. Khi bấm **Phân tích**, kết quả đã lưu tự động được gộp vào hồ sơ. Endpoint:

```http
GET /claims/{claim_id}/evidence/{evidence_id}/authenticity
```

chỉ dành cho dev, audit hoặc màn hình chi tiết muốn đọc lại báo cáo của đúng một ảnh. Người dùng nghiệp vụ không cần gọi endpoint này.

## Thiếu chứng từ hoặc dữ liệu quan hệ thì sao?

| Tình huống | Risk score | Trạng thái chung | Cách hiểu |
|---|---:|---|---|
| Đủ dữ liệu bảng, thiếu chứng từ | Có | `partial` | Vẫn xếp hàng ưu tiên; chưa đối chiếu được chứng từ |
| Đủ dữ liệu bảng, thiếu ảnh xe | Có | `partial` | Vẫn xếp hàng ưu tiên; chưa đánh giá hư hỏng/authenticity |
| Đủ dữ liệu bảng, chưa có entity/edge | Có | `partial` | Graph là `not_provided`, không được hiểu là không có quan hệ |
| Thiếu feature bắt buộc của XGBoost | Không | `blocked` | Các kiểm tra ảnh/chứng từ có thể chạy, nhưng không tạo risk score |
| Đủ mọi đầu vào và module cần thiết | Có | `complete` | Vẫn cần con người duyệt |

Risk score là điểm xếp hạng nghiên cứu từ dữ liệu bảng, không phải xác suất gian lận. Thiếu một nguồn bằng chứng không được tự động coi là hồ sơ “pass”, và cũng không tự động coi là gian lận.

## Media authenticity v2 đã nâng cấp gì?

1. **Provenance:** đọc EXIF/XMP/IPTC; có adapter ExifTool và C2PA.
2. **Watermark/provider:** chừa adapter cho SynthID; nếu chưa tích hợp thì ghi `unavailable`.
3. **Cross-claim reuse:** mỗi ảnh có SHA-256 và perceptual hash; ảnh giống hệt hoặc gần giống ảnh ở claim khác được gắn tín hiệu review tự động.
4. **Pixel feature capture:** lưu entropy, edge mean, độ lệch chuẩn kênh màu và bytes/pixel làm đầu vào cho model forensic sau này. Các feature này chưa bị áp threshold để kết luận thật/giả.
5. **Benchmark:** manifest giữ mọi biến thể của cùng ảnh trong cùng split; script đánh giá báo precision, recall, F1, false-positive rate và lỗi theo từng loại ảnh.

Cross-claim reuse là tín hiệu chống gian lận hữu ích nhưng không chứng minh ảnh do AI tạo. Ngược lại, detector pixel có điểm cao cũng không đủ để tự từ chối claim.

## Thiết kế benchmark cần thu thập

- ảnh camera gốc đúng miền tổn thất xe;
- chỉnh sáng, crop, resize và nén hợp lệ;
- ảnh qua Facebook, TikTok và ứng dụng chat;
- ảnh chụp lại màn hình hoặc ảnh in rồi chụp lại;
- ảnh sinh từ nhiều họ generator, gồm generator chưa xuất hiện trong train;
- ảnh thật được AI chỉnh sửa cục bộ;
- cùng một ảnh được tái sử dụng ở nhiều claim giả lập.

Ngưỡng chỉ được chọn trên validation và giữ nguyên khi mở test. Báo cáo phải tách kết quả theo generator chưa thấy, social re-encode, screen recapture và camera/device.

```powershell
python scripts/build_media_authenticity_benchmark.py <benchmark_root> <manifest.jsonl>
python scripts/evaluate_media_authenticity_benchmark.py <predictions.jsonl> --threshold <locked_threshold> --split test --output <report.json>
```

## Lớp phòng thủ nên thêm ở pilot

Detector sau khi upload không thể bao phủ mọi kiểu giả. Ứng dụng thu thập ảnh nên tạo phiên chụp có thời hạn và yêu cầu ngẫu nhiên, ví dụ chụp toàn cảnh rồi cận cảnh theo thứ tự, nghiêng máy sang trái, hoặc quay video ngắn quanh xe. Server lưu nonce, thời gian, thứ tự ảnh và hash ngay khi nhận. Nếu thiết bị hỗ trợ provenance có chữ ký thì xác minh thêm C2PA. Ảnh tải từ thư viện vẫn có thể nhận, nhưng mang mức bảo đảm thấp hơn ảnh chụp trong phiên.

Nghiên cứu gần đây cũng xem khả năng tổng quát sang generator chưa thấy là thách thức chính; dữ liệu đa dạng và kiểm thử sau nén/biến đổi là bắt buộc. Tham khảo [Community Forensics, CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/html/Park_Community_Forensics_Using_Thousands_of_Generators_to_Train_Fake_Image_CVPR_2025_paper.html), [SPAI, CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/html/Karageorgiou_Any-Resolution_AI-Generated_Image_Detection_by_Spectral_Learning_CVPR_2025_paper.html), và [C2PA Content Credentials](https://spec.c2pa.org/specifications/specifications/2.3/specs/ContentCredentials.html).
