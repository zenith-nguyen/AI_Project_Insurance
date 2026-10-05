# CarDD — trạng thái bàn giao cho Tú Anh

## Những gì đã biết

- Nguồn mirror đã dùng: Hugging Face `harpreetsahota/CarDD`; đây không phải nguồn chính thức.
- Project gốc: `cardd-ustc.github.io`.
- Đường dẫn backup được ghi nhận từ Colab: `/content/drive/MyDrive/AI_Project_Insurance/data/bronze/layerA_cardd/`.
- Cấu trúc download dự kiến là FiftyOne: `fiftyone.yml`, `samples.json`, `metadata.json`, `data/*.jpg` và file license.
- Không giả định annotation là COCO JSON trước khi đọc `samples.json` thực tế.

## Chưa được xác minh

| Mục | Trạng thái |
|---|---|
| Link Google Drive chia sẻ | Chưa được cung cấp |
| Tổng số ảnh | Chưa có kết quả; “2.823 files” của snapshot không phải image count |
| Sáu tên damage class | Chưa đọc được từ annotation thật |
| Annotation field/geometry | Chưa đọc được từ `samples.json` thật |
| Nội dung `CarDD_license.pdf` | Chưa đọc; chưa kết luận quyền dùng/phân phối |

## Cách hoàn tất

Sau khi đồng bộ folder về máy, chạy:

```powershell
.\.venv\Scripts\python.exe scripts\inspect_cardd.py "PATH_TO_layerA_cardd"
```

Script sẽ in số ảnh, số sample, loại annotation/geometry thực tế, các class tìm thấy và toàn bộ text trích từ license. Tú Anh cần gửi lại output này cùng link Drive; không public raw CarDD cho đến khi license được xác minh.
