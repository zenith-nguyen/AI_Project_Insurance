# Data Source Plan v1 — Nhánh chứng từ

**Ngày cập nhật:** 10/10/2026  
**Trạng thái:** nhóm đã có dữ liệu; chưa audit file thực tế trong workspace/Drive

## Mục tiêu

Các bộ dữ liệu công khai được dùng để xây và đánh giá module chứng từ độc lập: phân loại loại chứng từ, OCR, nhận diện vùng và trích xuất trường. Chúng không có `claim_id` chung với Kaggle fraud hoặc CarDD, nên không được ghép từng dòng và không được dùng để tuyên bố phát hiện gian lận claim-level.

## Vai trò dự kiến

| Nguồn | Vai trò phù hợp | Không dùng để kết luận |
|---|---|---|
| CORD v2 | Receipt parsing, OCR và key information extraction | Gian lận bảo hiểm |
| ICDAR2019 SROIE | OCR/field extraction trên hóa đơn, biên nhận | Claim fraud label |
| FUNSD | Hiểu cấu trúc form và quan hệ key-value | Chứng từ bảo hiểm Việt Nam đã được kiểm chứng |
| XFUND | Form understanding đa ngôn ngữ | Fraud hoặc consistency claim-level khi chưa có claim thật |
| MIDV | Nhận diện và trích xuất trường giấy tờ định danh | Xác minh danh tính production |
| RVL-CDIP | Phân loại loại tài liệu trước OCR | Trích xuất trường chi tiết; không cần tải toàn bộ nếu chỉ làm baseline phân loại |

## Cấu trúc lưu trữ đề xuất

```text
data/bronze/documents/
├── cord_v2/
├── sroie/
├── funsd/
├── xfund/
├── midv/
└── rvl_cdip_sample/
```

Raw data không commit Git. Mỗi nguồn cần một manifest riêng với tối thiểu:

| Trường manifest | Ý nghĩa |
|---|---|
| `dataset_name` | Tên và phiên bản nguồn |
| `source_url` | Nơi tải |
| `downloaded_at` | Ngày tải |
| `license_file` | File hoặc URL điều khoản |
| `split_original` | Split gốc của nguồn |
| `document_id` | ID duy nhất trong nguồn |
| `relative_path` | Đường dẫn tương đối |
| `sha256` | Kiểm tra toàn vẹn |
| `language` | Ngôn ngữ nếu có |
| `task` | classification/OCR/layout/KIE/ID |
| `annotation_available` | Có ground truth hay không |
| `claim_id` | Để trống với dữ liệu công khai không liên kết |

## Audit bắt buộc trước khi dùng

1. Đếm file, split, định dạng ảnh/PDF và dung lượng thật.
2. Kiểm tra file hỏng, trùng byte và gần trùng giữa train/validation/test.
3. Đọc license từng nguồn; lưu bằng chứng, phạm vi dùng và hạn chế phân phối.
4. Kiểm tra annotation schema, nhãn, ngôn ngữ, missing và class imbalance.
5. Xác nhận split gốc có theo document/template/identity hay không để tránh leakage.
6. Tạo sample gallery nhỏ để kiểm tra dữ liệu bằng mắt.
7. Lập data dictionary/knowledge base audit cho trường trích xuất.
8. Với RVL-CDIP, inventory trước rồi mới quyết định cỡ sample theo lớp; chưa cần sao chép toàn bộ khoảng 400.000 ảnh cho baseline.

## Ground truth v1 đề xuất

- Document classification: nhãn loại tài liệu từ split chính thức hoặc mapping được duyệt.
- OCR: CER/WER trên text ground truth chuẩn hóa theo quy tắc ghi rõ.
- Field extraction: exact match và normalized match theo từng trường.
- Layout/KIE: entity F1 và relation F1 nếu annotation hỗ trợ.
- Mọi quy tắc chuẩn hóa ngày, số tiền, dấu câu và Unicode phải được cố định trước test.
- Không dùng test để sửa prompt, mapping hoặc hậu xử lý.

## Chia train/validation/test

Ưu tiên split chính thức. Nếu phải tự chia, nhóm theo document/template/identity trước khi split để ảnh gần giống của cùng mẫu không nằm ở nhiều tập. Mọi lựa chọn model, OCR engine, prompt và hậu xử lý chỉ dùng train/validation; test mở một lần sau khi pipeline đã khóa.

## RAG/GenAI

Hiện chưa có RAG trong baseline. Nếu thêm RAG, cần tạo riêng:

- tập câu hỏi có đáp án và nguồn trích dẫn;
- danh sách tài liệu được phép truy xuất;
- metric retrieval như Recall@K/MRR;
- kiểm tra answer correctness, citation correctness và unsupported claim;
- log prompt/model/version;
- rule từ chối trả lời khi không có bằng chứng.

Không trộn test OCR/KIE với prompt tuning hoặc retrieval tuning.

## Bước tiếp theo khi nhận đường dẫn dữ liệu

Chạy inventory read-only cho sáu thư mục, xuất `document_sources_inventory.json`, sau đó mới quyết định nguồn nào dùng cho baseline v1 và cỡ sample RVL-CDIP.

