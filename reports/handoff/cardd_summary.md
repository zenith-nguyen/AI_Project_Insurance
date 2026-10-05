# CarDD — trạng thái bàn giao cho Tú Anh

## Kết quả đã xác minh trên Colab — 06/10/2026

- Nguồn mirror đã dùng: Hugging Face `harpreetsahota/CarDD`; đây không phải nguồn chính thức.
- Project gốc: `cardd-ustc.github.io`.
- Đường dẫn đã xác nhận cho Colab: `/content/drive/MyDrive/AI_Project_Insurance/data/bronze/layerA_cardd/`.
- Cấu trúc thực tế là FiftyOne: `fiftyone.yml`, `samples.json`, `metadata.json`, `data/*.jpg` và `CarDD_license.pdf`.
- Có 2.753 ảnh JPG và 2.816 sample record; hai số chưa khớp, chênh 63 record. Chưa chuyển đổi hoặc train trước khi audit mapping file.
- Annotation lưu trong `samples.json` dưới dạng `Detection`/`Detections`, có 12.422 `bounding_box` và 6.211 `mask`.
- Sáu lớp tìm thấy: `crack`, `dent`, `glass shatter`, `lamp broken`, `scratch`, `tire flat`.

## License đã đọc

`CarDD_license.pdf` nêu dataset thuộc PIC Lab, Chinese Academy of Sciences. Dùng cho nghiên cứu khoa học vẫn cần prior consent của PIC Lab; dùng thương mại cần được cho phép trước; không được chuyển giao, phân phối hoặc phát sóng toàn bộ hay một phần dữ liệu cho bên thứ ba khi chưa được ủy quyền; công bố sử dụng dữ liệu phải trích dẫn bài báo CarDD năm 2023, DOI `10.1109/TITS.2023.3258480`.

Trạng thái hiện tại: đã đọc điều khoản nhưng chưa có bằng chứng trong repo rằng nhóm đã nhận prior consent. Không chia sẻ raw data hoặc bắt đầu training dùng CarDD trước khi lưu xác nhận quyền sử dụng.

## Việc còn phải xác minh

| Mục | Trạng thái |
|---|---|
| Link Google Drive chia sẻ | Chưa được cung cấp; path trong MyDrive đã xác nhận |
| Mapping sample ↔ ảnh | 2.816 sample so với 2.753 ảnh; cần audit 63 record chênh lệch |
| Tính toàn vẹn ảnh | Chưa kiểm tra ảnh hỏng/truncated |
| Prior consent | Chưa có bằng chứng chấp thuận của PIC Lab trong repo |

## Bước tiếp theo

Chạy audit alignment trong Colab, sau đó chỉ chuyển annotation khi `ready_for_conversion` là `true`:

```python
!python scripts/audit_cardd_alignment.py "/content/drive/MyDrive/AI_Project_Insurance/data/bronze/layerA_cardd"
```
