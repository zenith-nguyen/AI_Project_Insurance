# Kiểm tra notebook và kế hoạch chuyển sang Google Drive mới

**Ngày kiểm tra:** 07/10/2026  
**Notebook:** `D:\My Dowload\AI_Project_Insurance_Car_Detect.ipynb`  
**SHA-256:** `20c5eb5a6a496d38e67f68618b714c1abe5c4ce4e30f4d88065ebb34bc5e8f9a`

## Kết luận nhanh

- Notebook tải về đọc được bình thường, dung lượng 267.770 bytes và có 75 code cell.
- Output cũ vẫn còn, nhưng toàn bộ `execution_count` đã bị đặt về `null`; vì vậy số thứ tự chạy trong notebook không còn đáng tin.
- Notebook không chứa giá trị Kaggle token hoặc Hugging Face token dạng chữ rõ. Nó chỉ có lệnh đọc `KAGGLE_API_TOKEN` từ Colab Secrets.
- Notebook lưu được tiến độ đến **conversion CarDD lần đầu** và validator báo hợp lệ.
- Notebook **không lưu** lần conversion v2 có split 1.966/431/419, không lưu thao tác cleanup Drive và chưa có YOLO training. Output v2 đã được gửi trong chat nhưng cần kiểm tra lại file thật trên Drive cũ.
- Không cần làm lại toàn bộ dự án. Cần kiểm kê Drive cũ, tái sử dụng Bronze và conversion metadata còn tốt, rồi tiếp tục trên Drive mới.

## Cập nhật sau khi mount Drive mới

- Shortcut `AI_Project_Insurance_OLD` đã xuất hiện trong My Drive mới và Colab đọc được.
- Checker trả `Bronze ready: True`, xác nhận dữ liệu nguồn qua shortcut vẫn dùng được.
- Checker trả `Conversion metadata ready: False` và `Actual splits: {}`. Nghĩa là Drive cũ không cung cấp đủ `conversion_report.json`, `split_manifest.jsonl` và labels để resume trực tiếp.
- Hướng xử lý: giữ Bronze qua shortcut cũ, chạy lại converter v2 trên Drive mới với `--image-mode labels-only`, rồi dựng training view tạm trong `/content`. Không tải lại ảnh và không copy 2.816 ảnh sang Processed.
- Notebook resume v2 đã sửa lỗi UTF-8 và tự thực hiện nhánh recovery này.

## Kết quả recovery trên Drive mới

Recovery đã hoàn tất thành công ngày 07/10/2026:

- Bronze qua shortcut: `PASS`.
- Conversion v2 metadata: `PASS`.
- Labels: 2.816 file.
- Split: train 1.966, validation 431, test 419.
- Dataset tạm: `/content/cardd_yolo_v1/data.yaml`.
- Validator: `valid: true`.
- Số ảnh copy trong Processed trên Drive mới: 0.

Processed trên Drive mới hiện chỉ giữ labels, split manifest và conversion report. Ảnh được đọc từ Bronze qua shortcut Drive cũ và liên kết vào `/content` khi cần chạy model.

## Trạng thái tìm thấy trong notebook

### Tabular

- Đã tải workbook Kaggle 1.000 dòng × 39 cột.
- Phân bố nhãn: 753 non-fraud và 247 fraud.
- Đã tạo Silver 1.000 dòng × 42 cột, chuẩn hóa missing value và ngày tháng.
- Lỗi mixed type ở `auto_model` đã được tìm ra và sửa bằng cách chuyển sang string.
- Silver Parquet đã từng được ghi và đọc lại thành công; manifest có SHA-256 `b56048c246424b9ba5ed9ca2e651c8b7b218fc26524415a08f29bd8451ae200d`.
- Một cell `ls` sau đó báo không thấy thư mục Silver, có thể do trạng thái mount/runtime khác nhau. Repo local hiện có pipeline tabular hoàn chỉnh hơn notebook này, vì vậy không dùng notebook cũ để dựng lại nhánh tabular.

### CarDD

- Đã tải `samples.json` và inspect đúng định dạng FiftyOne.
- Ban đầu có 2.753 ảnh cho 2.816 sample; đã tải bù đủ 63 ảnh.
- Kiểm tra cuối trong notebook: 2.816 sample, 2.816 ảnh, không thiếu/thừa/hỏng.
- Đã profile 6.211 damage object, giải mã mask zlib/NumPy và smoke test polygon thành công.
- Conversion lần đầu dùng `--image-mode auto`, tạo 2.816 bản copy ảnh trong Processed.
- Conversion lần đầu có split train 2.029, validation 394, test 393; validator báo `valid: true`.
- Conversion v2 có split tốt hơn 1.966/431/419 đã chạy sau đó theo output trong chat, nhưng không có cell/output tương ứng trong notebook tải về.
- Chưa có cell training YOLOv8-seg.

## Ba lỗi lịch sử trong notebook

| Lỗi | Ý nghĩa | Trạng thái |
|---|---|---|
| Colab Secret timeout | Cell được gọi ngoài ngữ cảnh Colab UI | Không ảnh hưởng dữ liệu; lần tải Kaggle sau đó thành công |
| Drive mountpoint có file | `/content/drive` chứa thư mục local | Đã xử lý bằng cách dời thư mục và mount lại |
| `auto_model` lẫn string/int | PyArrow không ghi được Parquet | Đã chuyển cột sang string và ghi Silver thành công |

## Cách chuyển nhanh nhất

Không dùng notebook cũ để chạy lại từ cell đầu. Notebook này chỉ giữ làm lịch sử.

1. Từ tài khoản Drive cũ, chia sẻ thư mục `AI_Project_Insurance` cho tài khoản mới và cấp quyền phù hợp.
2. Trong Drive mới, thêm shortcut của thư mục cũ vào My Drive với tên dễ nhận biết, ví dụ `AI_Project_Insurance_OLD`.
3. Tạo thư mục ghi mới `AI_Project_Insurance` trong Drive mới.
4. Mở notebook resume sạch bằng tài khoản mới, mount Drive mới và chạy `check_cardd_resume_state.py` trên shortcut cũ.
5. Chỉ tiếp tục nếu kết quả cho thấy:
   - `bronze.ready: true`;
   - `bronze.sample_records: 2816`;
   - `bronze.image_files: 2816`;
   - `conversion.metadata_ready: true`;
   - split v2 là train 1.966, validation 431 và test 419.
6. Copy sang Drive mới code, reports, labels, `split_manifest.jsonl` và `conversion_report.json`; không copy `processed/cardd_yolo_v1/images`.
7. Dùng Bronze qua shortcut làm nguồn đọc trong giai đoạn đầu. Khi cần tách hẳn tài khoản cũ, chuyển đúng một bản Bronze sang Drive mới rồi so sánh hash trước khi xóa bản cũ.
8. Dựng dataset YOLO tạm trong `/content`, chạy validator v2 và chỉ sau đó mới bắt đầu training.

## Nếu Drive cũ chỉ còn conversion v1

Nếu checker trả split 2.029/394/393, notebook và Drive cũ chỉ còn conversion lần đầu. Khi đó vẫn không cần tải lại CarDD nếu Bronze đủ 2.816 ảnh. Chạy converter mới với seed `20261006` và chế độ mặc định `labels-only`; converter sẽ tạo lại split v2 mà không copy ảnh vào Drive.

## Nếu shortcut Drive không đọc được trong Colab

Ổ `D:` trên máy còn khoảng 26 GB tại lần kiểm tra gần nhất. Có thể dùng Google Drive Desktop hoặc trình duyệt để tải một bản Bronze về máy, kiểm tra đủ file/hash, rồi upload sang tài khoản mới. Không xóa dữ liệu ở tài khoản cũ trước khi checker trên tài khoản mới báo Bronze hoàn chỉnh.

## Bảo mật

Notebook không chứa raw token, nhưng Kaggle API token đã từng được gửi trong nội dung chat. Nên thu hồi token cũ và tạo token mới trước khi dùng tài khoản/Drive mới. Lưu token mới trong Colab Secrets; không đặt token trực tiếp trong notebook.
