# Kế hoạch huấn luyện CarDD YOLOv8-seg

**Phiên bản:** v1 — 07/10/2026  
**Trạng thái dữ liệu:** 2.816 ảnh, 6.211 damage object, validator đạt, Processed không copy ảnh.

## Mục tiêu

Huấn luyện mô hình instance segmentation nhận diện sáu loại hư hại: `crack`, `dent`, `glass shatter`, `lamp broken`, `scratch`, `tire flat`. Đây là nhánh đánh giá hư hại độc lập; output chưa phải tín hiệu fraud và chưa liên kết với hồ sơ Kaggle.

## Protocol cố định

| Thành phần | Cấu hình |
|---|---|
| Baseline | `yolov8n-seg.pt`, pretrained |
| Ảnh | 640 px |
| Split | Train 1.966 / validation 431 / test 419 |
| Seed dữ liệu | 20261006 |
| Seed training | 20261007 |
| Batch | 8 |
| Epoch tối đa | 100 |
| Early stopping | patience 20 |
| Checkpoint | mỗi 10 epoch; giữ `best.pt` và `last.pt` |
| Metric chọn model | validation mask mAP50-95 |
| Test | chạy một lần sau khi khóa model/checkpoint |

[Tài liệu instance segmentation của Ultralytics](https://docs.ultralytics.com/tasks/segment/) mô tả cách train từ pretrained weights và báo riêng box/mask mAP. [Tài liệu validation](https://docs.ultralytics.com/modes/val/) cho phép chọn rõ split `val` hoặc `test`. Project dùng API này nhưng giữ YOLOv8n-seg để nhất quán với baseline đã thống nhất.

## Trình tự chạy

1. Bật GPU trong Colab và xác nhận CUDA/GPU memory.
2. Copy ảnh từ shortcut Drive cũ vào `/content` để tăng tốc đọc; bản copy này là tạm và không tốn Drive.
3. Chạy validator và preflight: đủ ảnh/label ở cả ba split, CUDA hoạt động, local disk còn ít nhất 5 GB.
4. Smoke test: 2 epoch, 10% train. Mục tiêu chỉ là kiểm tra pipeline, loss hữu hạn và checkpoint được tạo.
5. Baseline: train tối đa 100 epoch, early stopping theo validation.
6. Đánh giá `best.pt` trên validation; lưu box/mask mAP50-95, mAP50, mAP75 và metric theo từng lớp.
7. Chỉ cân nhắc YOLOv8s-seg nếu GPU/time cho phép; so sánh trên validation, không đọc test.
8. Khóa model và checkpoint. Sau đó mới chạy test đúng một lần và ghi rõ ngày, hash/config.

## Điều kiện đạt kỹ thuật

- Smoke test tạo được `best.pt` và `last.pt`.
- Không có NaN/Inf trong loss.
- Validation hoàn tất cho đủ sáu lớp.
- Report có metric mask và box, gồm kết quả từng lớp; không chỉ báo một mAP tổng.
- Checkpoint, `args.yaml`, `results.csv`, plots và manifest được lưu trên Drive mới.
- Không tuyên bố production readiness hoặc fraud detection từ kết quả CarDD.

## Xử lý gián đoạn Colab

Checkpoint được ghi lên Drive mới. Nếu runtime ngắt, dựng lại dataset tạm trong `/content`, rồi resume từ `last.pt`. Không chạy lại conversion và không dùng test để quyết định có resume/tune hay không.

## Việc cần lưu trước khi công bố kết quả

- Bằng chứng prior consent của PIC Lab và trích dẫn DOI `10.1109/TITS.2023.3258480`.
- Phiên bản Ultralytics, GPU, seed và toàn bộ training config.
- Validation metrics, per-class metrics và một số prediction mẫu.
- Final test metrics chỉ sau khi model selection hoàn tất.
