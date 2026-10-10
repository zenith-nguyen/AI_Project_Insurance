# Ground Truth Definition v1

## Mục tiêu

Tài liệu định nghĩa nhãn nào được xem là ground truth, cách sử dụng nhãn và điều kiện để một mẫu được đưa vào metric. Ground truth của các dataset public không được tự động xem là ground truth nghiệp vụ bảo hiểm Việt Nam.

## CarDD damage segmentation

- Đơn vị mẫu: một ảnh xe.
- Đơn vị nhãn: polygon segmentation và class của từng vùng hư hỏng.
- Classes: crack, dent, glass shatter, lamp broken, scratch, tire flat.
- Một ảnh có thể có nhiều instance và nhiều class.
- Mẫu hợp lệ khi ảnh decode được, label tồn tại, polygon có đủ điểm và tọa độ chuẩn hóa nằm trong miền hợp lệ.
- Train/validation/test được khóa từ manifest; test không dùng để điều chỉnh threshold hoặc chọn checkpoint.

## Document classification

- Ground truth là class tài liệu do dataset cung cấp.
- RVL-CDIP sample dùng taxonomy 16 lớp của RVL-CDIP.
- Taxonomy này chỉ dùng benchmark nghiên cứu; khi có chứng từ bảo hiểm thật phải xây taxonomy nghiệp vụ mới và có hướng dẫn gán nhãn.
- Metric chính: macro-F1; báo cáo thêm balanced accuracy và per-class F1.

## OCR

- Ground truth là chuỗi ký tự transcription gắn với ảnh/region trong source annotation.
- Chuẩn hóa trước metric phải được khóa: Unicode normalization, xử lý khoảng trắng và quy tắc chữ hoa/thường.
- Không tự sửa chính tả ground truth sau khi xem prediction.
- Metric: CER, WER và exact match; phải lưu cả kết quả trước và sau normalization.

## Key Information Extraction

- Ground truth gồm field name, field value và khi có thì bounding box/entity relation.
- CORD/SROIE/FUNSD/XFUND có schema khác nhau; mapping sang schema chung phải lưu `source_field`, `canonical_field` và transformation version.
- Field không có trong source được đánh dấu `not_available`, không tính là negative ngầm.
- Metric: precision, recall, micro-F1, macro-F1 và exact match theo field.

## Adjudication cho dữ liệu bảo hiểm thật

1. Hai người gán nhãn độc lập cho tập evaluation quan trọng.
2. Bất đồng được một reviewer nghiệp vụ giải quyết.
3. Ghi annotation guideline version, annotator role và thời điểm.
4. Không đưa PII thô vào report hoặc source control.
5. Mọi sửa ground truth sau evaluation phải tạo version mới và không ghi đè kết quả cũ.

## RAG/citation

RAG chưa được chọn làm baseline nên chưa có prompt/retrieval test set. Nếu scope mở RAG, citation ground truth phải chỉ ra document ID, page/region và đoạn nguồn hỗ trợ từng claim; câu trả lời không có bằng chứng phải được đánh dấu unsupported.
