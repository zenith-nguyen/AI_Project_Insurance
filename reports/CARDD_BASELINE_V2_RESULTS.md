# Kết quả CarDD YOLOv8n-seg baseline v2

**Ngày chạy:** 07/10/2026  
**Nguồn:** log Colab và `cardd_yolo_validation_before_training_v2.json` / `cardd_yolov8n_seg_val_v2.json` trên Google Drive  
**Trạng thái tại thời điểm baseline:** test chưa được sử dụng; `RUN_FINAL_TEST = False`. Sau model selection, YOLOv8s được khóa và final test đã chạy đúng một lần; xem `CARDD_FINAL_TEST_V1.md`.

## Dữ liệu và môi trường

- CarDD FiftyOne đã chuyển sang YOLO segmentation: 2.816 ảnh, 6.211 instance, 6 lớp.
- Split cố định: train 1.966 ảnh / validation 431 ảnh / test 419 ảnh.
- Validation có 935 instance; không thiếu label, không orphan label, không có dòng label lỗi.
- Ultralytics 8.4.173, Python 3.13.15, Torch 2.11.0 + CUDA 13.0, Tesla T4.
- Model: `yolov8n-seg.pt`, ảnh 640, batch 8, tối đa 100 epoch, seed 20261007.
- Huấn luyện hoàn tất 100 epoch trong khoảng 2,126 giờ; `best.pt` và `last.pt` đã lưu trên Drive.

## Kết quả validation của `best.pt`

| Metric | Kết quả |
|---|---:|
| Box precision | 0,705 |
| Box recall | 0,713 |
| Box mAP50 | 0,698 |
| Box mAP50-95 | 0,538 |
| Mask precision | 0,708 |
| Mask recall | 0,699 |
| Mask mAP50 | 0,697 |
| Mask mAP50-95 | 0,518 |
| Mask mAP75 | 0,538 |

| Lớp | Số instance validation | Mask mAP50-95 |
|---|---:|---:|
| crack | 98 | 0,0649 |
| dent | 272 | 0,2960 |
| glass shatter | 71 | 0,8721 |
| lamp broken | 75 | 0,6590 |
| scratch | 385 | 0,2636 |
| tire flat | 34 | 0,9496 |

## Diễn giải

Baseline đã học được tín hiệu segmentation rõ ràng và pipeline GPU hoạt động đúng. Hiệu năng giữa các lớp không đồng đều: `tire flat` và `glass shatter` rất cao, `lamp broken` khá tốt, trong khi `crack`, `scratch` và `dent` còn yếu. Số instance không giải thích toàn bộ chênh lệch vì `scratch` là lớp nhiều nhất nhưng mask AP vẫn thấp; cần xem prediction mẫu, kích thước vật thể, độ mảnh của mask và mức mơ hồ annotation.

Confusion matrix chuẩn hóa và ba batch prediction được xem ngày 07/10/2026 cho thấy tỷ lệ đúng trên đường chéo lần lượt khoảng 0,64 (`crack`), 0,71 (`dent`), 0,96 (`glass shatter`), 0,79 (`lamp broken`), 0,74 (`scratch`) và 0,76 (`tire flat`) tại cấu hình vẽ confusion matrix của Ultralytics. Cột background cho thấy false positive tập trung nhiều ở `scratch`, `dent` và `crack`. Prediction mẫu cũng có các mask `scratch`/`dent` phủ rộng hoặc chồng lấn, trong khi vết nứt nhỏ có confidence và chất lượng biên thấp. Đây là quan sát định tính từ validation, không phải metric test.

Kết quả trên là validation lịch sử của baseline để chọn mô hình. Metric test hiện đã có cho checkpoint YOLOv8s được chọn, nhưng không làm thay đổi kết quả baseline này. Không dùng các con số CarDD để tuyên bố production readiness hay khả năng phát hiện gian lận. CarDD chỉ đo nhận diện hư hại; chưa có `claim_id` chung với dữ liệu fraud tabular.

## Quyết định trước final test

1. Giữ test khóa.
2. Chạy đúng một candidate YOLOv8s-seg với cùng split, kích thước ảnh, seed và protocol; không đọc test.
3. Chọn model bằng validation mask mAP50-95; dùng metric từng lớp và chi phí suy luận làm tiêu chí phụ.
4. Nếu chênh lệch validation rất nhỏ, ưu tiên YOLOv8n-seg vì nhẹ hơn và ghi rõ giới hạn ở các lớp vết mảnh.
5. Khóa model/checkpoint, sau đó mới chạy final test đúng một lần.

## Artifact trên Drive

- Checkpoint: `artifacts/image/cardd_yolov8n_seg_baseline_v2/weights/best.pt`
- Training artifacts: `artifacts/image/cardd_yolov8n_seg_baseline_v2/`
- Validation plots: `artifacts/image/evaluation/cardd_yolov8n_seg_val_v2/`
- Validation JSON: `reports/metrics/cardd_yolov8n_seg_val_v2.json`
