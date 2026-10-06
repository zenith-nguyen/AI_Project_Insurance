# CarDD — trạng thái bàn giao cho Tú Anh

## Kết quả đã xác minh trên Colab — 06/10/2026

- Nguồn mirror đã dùng: Hugging Face `harpreetsahota/CarDD`; đây không phải nguồn chính thức.
- Project gốc: `cardd-ustc.github.io`.
- Đường dẫn đã xác nhận cho Colab: `/content/drive/MyDrive/AI_Project_Insurance/data/bronze/layerA_cardd/`.
- Cấu trúc thực tế là FiftyOne: `fiftyone.yml`, `samples.json`, `metadata.json`, `data/*.jpg` và `CarDD_license.pdf`.
- Lần tải đầu có 2.753 ảnh cho 2.816 sample record. Audit xác định đúng 63 ảnh được annotation tham chiếu nhưng chưa tải; không có record thiếu filepath, ảnh thừa hoặc filename trùng.
- Đã tải bù 63 ảnh từ cùng mirror. Kiểm tra cuối có 2.816 sample, 2.816 ảnh, không thiếu/thừa và không có ảnh hỏng; `ready_for_conversion: true`. Kết quả lưu tại `reports/cardd_alignment_final.json` trên Drive.
- Annotation lưu song song trong hai field FiftyOne: `detections` có 6.211 box và `segmentations` có cùng 6.211 box kèm mask `$binary`. Vì vậy dataset có 6.211 damage object; con số 12.422 box của inspector đầu tiên là đếm cùng object ở cả hai field.
- Mask `$binary` đã được xác minh là mảng NumPy boolean 2D nén bằng zlib và mã hóa base64. Detection và segmentation ghép đúng theo thứ tự: 6.211 cặp, không lệch label hoặc bounding box.
- Sáu lớp tìm thấy: `crack`, `dent`, `glass shatter`, `lamp broken`, `scratch`, `tire flat`.
- Tất cả 2.816 sample đều có annotation; dataset không cung cấp tag/split sẵn.
- Conversion YOLO segmentation v2 đã hoàn tất với seed `20261006`: train 1.966 ảnh, validation 431 ảnh và test 419 ảnh; tổng 6.211 object. Phân bố từng lớp gần 70/15/15 và một nhóm near-duplicate gồm hai ảnh được giữ trong cùng split. Validator v2 cần chạy lần cuối trước khi training.
- Để tiết kiệm Drive, chỉ giữ một bản ảnh trong Bronze. Thư mục processed giữ labels, split manifest và conversion report; bản YOLO đầy đủ được dựng tạm trong `/content` trước khi validation/training.

## License đã đọc

`CarDD_license.pdf` nêu dataset thuộc PIC Lab, Chinese Academy of Sciences. Dùng cho nghiên cứu khoa học vẫn cần prior consent của PIC Lab; dùng thương mại cần được cho phép trước; không được chuyển giao, phân phối hoặc phát sóng toàn bộ hay một phần dữ liệu cho bên thứ ba khi chưa được ủy quyền; công bố sử dụng dữ liệu phải trích dẫn bài báo CarDD năm 2023, DOI `10.1109/TITS.2023.3258480`.

Trạng thái hiện tại: đã đọc điều khoản nhưng chưa có bằng chứng trong repo rằng nhóm đã nhận prior consent. Không chia sẻ raw data hoặc bắt đầu training dùng CarDD trước khi lưu xác nhận quyền sử dụng.

## Việc còn phải xác minh

| Mục | Trạng thái |
|---|---|
| Link Google Drive chia sẻ | Chưa được cung cấp; path trong MyDrive đã xác nhận |
| Mapping sample ↔ ảnh | Đã sạch: 2.816 ↔ 2.816 |
| Tính toàn vẹn ảnh | Đã verify bằng Pillow; 0 ảnh hỏng/truncated |
| Cấu trúc mask chi tiết | Đã xác minh và convert thành YOLO segmentation |
| Split train/val/test | Đã tạo bằng multilabel stratification; không có near-duplicate chéo split |
| Prior consent | Chưa có bằng chứng chấp thuận của PIC Lab trong repo |

## Bước tiếp theo

Lưu bằng chứng prior consent của PIC Lab, dựng training view tạm trong `/content`, chạy validator v2, rồi mới bắt đầu baseline YOLOv8-seg. Không cần tải hoặc repair thêm ảnh.
