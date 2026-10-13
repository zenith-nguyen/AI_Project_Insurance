# Media Authenticity v1 — phát hiện dấu hiệu ảnh AI và provenance

## Người dùng sẽ thấy gì?

Khi ảnh được tải lên, hệ thống tạo SHA-256, đọc metadata, kiểm tra Content Credentials nếu máy chủ có `c2patool`, và trả các bằng chứng dưới nhóm `authenticity`. Kết quả dùng để ưu tiên kiểm tra thủ công; nó không tự kết luận gian lận và không tự từ chối hồ sơ.

| Tầng kiểm tra | Bản v1 | Cách hiểu |
|---|---|---|
| EXIF/XMP/IPTC | Đã chạy cục bộ | Tìm tên công cụ tạo ảnh và khai báo `trainedAlgorithmicMedia` |
| ExifTool | Adapter tùy chọn | Đọc metadata rộng hơn khi máy chủ đã cài ExifTool |
| C2PA Content Credentials | Adapter tùy chọn qua `c2patool` | Kiểm manifest, assertion và vấn đề validation |
| SynthID | Chưa có detector local tích hợp | Ghi rõ `unavailable`; không giả định “không có watermark” |
| Forensic classifier | Chưa train/validate | Chỉ bổ sung sau khi có tập ảnh bảo hiểm thật/AI đúng miền |

## Quy tắc kết luận

- `ai_provenance_detected`: C2PA có assertion về nội dung sinh bởi thuật toán.
- `provenance_problem`: provenance có dấu hiệu validation lỗi hoặc không khớp.
- `review`: metadata thường có thể sửa/xóa nhưng chứa dấu hiệu công cụ AI.
- `inconclusive`: chưa có bằng chứng dương tính. Trạng thái này **không có nghĩa ảnh thật**.

Content Credentials cung cấp provenance có thể kiểm chứng bằng chữ ký và content binding; chính C2PA lưu ý provenance là tín hiệu để đánh giá, không phải phán quyết nội dung “tốt/xấu”. [C2PA specification](https://spec.c2pa.org/specifications/)

SynthID là watermark nằm trong nội dung do các hệ thống hỗ trợ tạo ra. Google cũng nói công nghệ này không phải giải pháp tuyệt đối và ảnh không có SynthID có thể vẫn là ảnh AI từ nguồn khác. [Google DeepMind SynthID](https://deepmind.google/models/synthid/)

Meta mô tả việc gắn nhãn bằng C2PA/IPTC và watermark vô hình. Nhãn trên mạng xã hội vì vậy là kết quả của marker/provenance mà nền tảng nhận ra; không phải detector phổ quát cho mọi ảnh AI. [Meta AI labels](https://about.fb.com/news/2024/02/labeling-ai-generated-images-on-facebook-instagram-and-threads/)

## Threat model và giới hạn

1. Người nộp có thể xóa hoặc sửa EXIF/XMP.
2. Facebook, TikTok, ứng dụng chat hoặc thao tác chụp lại màn hình có thể làm mất metadata/provenance.
3. AI generator không hỗ trợ C2PA/SynthID sẽ không để lại marker tương ứng.
4. Metadata dạng text có thể bị giả mạo; C2PA chỉ mạnh khi chữ ký, binding và trust chain đều hợp lệ.
5. Forensic detector có thể giảm chất lượng khi gặp model tạo ảnh mới, resize, crop, nén hoặc ảnh bảo hiểm khác miền train.
6. Ảnh AI không tự động đồng nghĩa claim gian lận; ảnh chỉnh sửa hợp lệ cũng có thể được dùng để che PII hoặc chú thích tổn thất.

## Việc cần làm trước pilot

1. Cài và pin phiên bản `c2patool`; cache C2PA trust list theo chính sách vận hành.
2. Cài ExifTool trong container và lưu phiên bản tool cùng kết quả.
3. Nếu có quyền truy cập SynthID Detector/API phù hợp, xây adapter riêng và lưu raw provider response.
4. Tạo benchmark bảo hiểm Việt Nam gồm camera-original, chỉnh sáng/crop/nén, social-media re-encode, ảnh sinh AI và ảnh in/chụp lại.
5. Đo precision/recall theo từng loại biến đổi; khóa threshold trên validation trước test.
6. Hiển thị bằng chứng cho GĐV và luôn cho phép phản hồi/kháng nghị.
