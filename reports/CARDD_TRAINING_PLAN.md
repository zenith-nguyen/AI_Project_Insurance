# Kế hoạch huấn luyện CarDD YOLOv8-seg

**Phiên bản:** v2 — 07/10/2026
**Trạng thái dữ liệu:** 2.816 ảnh, 6.211 đối tượng hư hại, split và nhãn đã được kiểm tra.

**Trạng thái chạy:** YOLOv8n-seg baseline v2 đã hoàn tất 100 epoch; validation mask mAP50-95 = 0,518 và box mAP50-95 = 0,538. Notebook candidate YOLOv8s-seg đã sẵn sàng. Final test vẫn khóa. Chi tiết baseline tại `reports/CARDD_BASELINE_V2_RESULTS.md`.

## Mục tiêu

Huấn luyện mô hình instance segmentation nhận diện sáu loại hư hại: `crack`, `dent`, `glass shatter`, `lamp broken`, `scratch`, `tire flat`. Đây là nhánh đánh giá hư hại độc lập. Kết quả CarDD chưa phải tín hiệu gian lận và chưa liên kết với hồ sơ bồi thường Kaggle.

## Cấu hình cố định

| Thành phần | Cấu hình |
|---|---|
| Notebook chính | `CarDD_YOLOv8_Training_v2.ipynb` |
| Baseline | `yolov8n-seg.pt`, pretrained |
| Candidate | `CarDD_YOLOv8s_Candidate_v1.ipynb`, model `yolov8s-seg.pt` |
| Candidate khi đổi tài khoản | `CarDD_YOLOv8s_Candidate_Pro_Account_v2.ipynb` |
| Kích thước ảnh | 640 px |
| Split | Train 1.966 / validation 431 / test 419 |
| Seed dữ liệu / training | 20261006 / 20261007 |
| Batch | 8 |
| Epoch tối đa | 100 |
| Early stopping | patience 20 |
| Checkpoint | mỗi 10 epoch; giữ `best.pt` và `last.pt` |
| Metric chọn model | validation mask mAP50-95 |
| Quy tắc model lớn | Chỉ chọn YOLOv8s nếu tăng ít nhất 0,0100 mask mAP50-95 |
| Test | chạy một lần sau khi khóa model và checkpoint |

## Trình tự chạy

1. Chọn T4 GPU, gắn Drive và kiểm tra CUDA.
2. Kiểm tra SHA-256 của `samples.json`, conversion report, manifest và 2.816 label.
3. Dựng dataset tạm trong `/content`. Cell hiển thị tiến độ, thử lại file lỗi và tiếp tục từ `.building` nếu lần trước bị ngắt.
4. Xác nhận số ảnh/nhãn từng split, định dạng polygon và tổng 6.211 instance.
5. Smoke test 2 epoch trên 10% train để kiểm tra CUDA, loss và checkpoint.
6. Baseline tối đa 100 epoch, early stopping theo validation; checkpoint lưu trên Drive mới.
7. Đánh giá `best.pt` trên validation và lưu box/mask mAP cùng metric từng lớp.
8. Chạy YOLOv8s-seg trên đúng train/validation và cùng cấu hình so sánh.
9. Chọn YOLOv8s khi tăng ít nhất 0,0100 mask mAP50-95; nếu không thì giữ YOLOv8n nhẹ hơn.
10. Ghi SHA-256 của checkpoint được chọn, khóa checkpoint rồi mới tạo cell final test chạy đúng một lần.

## Khả năng phục hồi

- Nếu copy ảnh bị ngắt, chạy lại cell staging; file đủ kích thước được dùng lại.
- Nếu training bị ngắt và đã có `last.pt`, chạy lại cell training để resume.
- Nếu `best.pt` đã tồn tại, notebook dùng lại và không train chồng lên run cũ.
- Test bị khóa bằng `RUN_FINAL_TEST = False` và từ chối chạy lần hai khi report đã tồn tại.

## Điều kiện đạt kỹ thuật

- Smoke test tạo `best.pt` và `last.pt`; loss không có NaN/Inf.
- Validation hoàn tất cho đủ sáu lớp.
- Báo cáo có mask và box mAP50-95, mAP50, mAP75 cùng metric từng lớp.
- Checkpoint, `results.csv`, plots và manifest được lưu trên Drive mới.
- Không tuyên bố production readiness hoặc khả năng phát hiện gian lận từ riêng CarDD.

## Điều kiện sử dụng dữ liệu

Trước khi công bố kết quả, nhóm cần lưu bằng chứng prior consent của PIC Lab và trích dẫn DOI `10.1109/TITS.2023.3258480` theo giấy phép CarDD.
