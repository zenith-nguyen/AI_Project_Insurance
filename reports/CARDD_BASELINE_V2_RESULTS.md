# Kết quả CarDD YOLOv8n-seg baseline v2

**Ngày chạy:** 07/10/2026  
**Nguồn:** log Colab và `cardd_yolo_validation_before_training_v2.json` / `cardd_yolov8n_seg_val_v2.json` trên Google Drive  
**Trạng thái test:** chưa sử dụng; `RUN_FINAL_TEST = False`

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

Kết quả trên là validation để chọn mô hình. Chưa có metric test và không được dùng các con số này để tuyên bố production readiness hay khả năng phát hiện gian lận. CarDD chỉ đo nhận diện hư hại; chưa có `claim_id` chung với dữ liệu fraud tabular.

## Quyết định trước final test

1. Giữ test khóa.
2. Xem confusion matrix, PR curves và prediction mẫu của ba lớp yếu.
3. Quyết định một lần xem có chạy candidate YOLOv8s-seg cùng split/config hay khóa YOLOv8n-seg ngay.
4. Nếu có candidate, chỉ so sánh trên validation mask mAP50-95 và metric từng lớp.
5. Khóa model/checkpoint, sau đó mới chạy final test đúng một lần.

## Artifact trên Drive

- Checkpoint: `artifacts/image/cardd_yolov8n_seg_baseline_v2/weights/best.pt`
- Training artifacts: `artifacts/image/cardd_yolov8n_seg_baseline_v2/`
- Validation plots: `artifacts/image/evaluation/cardd_yolov8n_seg_val_v2/`
- Validation JSON: `reports/metrics/cardd_yolov8n_seg_val_v2.json`
