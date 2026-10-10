# CarDD — Model Selection v1

**Ngày khóa model:** 10/10/2026  
**Trạng thái:** đã chọn model bằng validation; final-test report và execution lock đã tồn tại trên Drive, đang chờ đọc/xác minh metric
**Test đã dùng để chọn model:** không

## Kết luận

Chọn **YOLOv8s-seg candidate v1**. Candidate đạt mask mAP50-95 `0,528379`, cao hơn YOLOv8n baseline `0,517514` một lượng `0,010865`. Quy tắc đã đặt trước yêu cầu model lớn phải tăng ít nhất `0,010000`, vì vậy candidate vượt ngưỡng và được khóa cho final test.

Checkpoint đã chọn:

```text
/content/drive/MyDrive/AI_Project_Insurance_Acc 2/artifacts/image/cardd_yolov8s_seg_candidate_v1/weights/best.pt
```

SHA-256:

```text
6c0d828760a427d48623653dcd6fffeb1cf591045d9ce8b8684a1d0f5f89420b
```

## So sánh validation

| Chỉ số | YOLOv8n baseline | YOLOv8s candidate | Chênh lệch |
|---|---:|---:|---:|
| Mask mAP50-95 | 0,5175 | **0,5284** | **+0,0109** |
| Mask mAP50 | 0,6974 | **0,6980** | +0,0006 |
| Box mAP50-95 | 0,5377 | **0,5570** | khoảng +0,0193 |

| Lớp | Baseline mask mAP50-95 | Candidate | Chênh lệch |
|---|---:|---:|---:|
| crack | 0,0649 | **0,0991** | **+0,0342** |
| dent | **0,2960** | 0,2875 | -0,0085 |
| glass shatter | 0,8721 | **0,9015** | **+0,0295** |
| lamp broken | **0,6590** | 0,6560 | -0,0030 |
| scratch | **0,2636** | 0,2543 | -0,0093 |
| tire flat | 0,9496 | **0,9719** | **+0,0223** |

Candidate cải thiện metric tổng và cải thiện `crack`, lớp yếu nhất của baseline. Tuy nhiên, `dent`, `lamp broken` và `scratch` giảm nhẹ. Báo cáo phải giữ cả hai mặt này; không nên mô tả candidate tốt hơn trên mọi lớp.

## Chi phí mô hình

| Thuộc tính từ log Colab | YOLOv8n | YOLOv8s |
|---|---:|---:|
| Tham số | khoảng 3,26 triệu | khoảng 11,78 triệu |
| Kích thước `best.pt` | khoảng 6,8 MB | khoảng 23,9 MB |
| Inference validation | khoảng 3,5 ms/ảnh | khoảng 13,6 ms/ảnh |

YOLOv8s lớn hơn và chậm hơn đáng kể. Quyết định chọn model dựa trên quy tắc validation đã đặt trước; chi phí triển khai cần được đo lại trên thiết bị đích nếu đi xa hơn mức nghiên cứu.

## Protocol đã dùng

- Cùng split cố định: train 1.966 ảnh, validation 431 ảnh, test 419 ảnh.
- Cùng kích thước ảnh 640, batch 8, seed 20261007 và tối đa 100 epoch.
- Candidate resume từ epoch 74 và hoàn tất đến epoch 100.
- Validation có 431 ảnh và 935 instance.
- Test không có trong candidate `data.yaml` và chưa được model selection đọc.
- File lựa chọn trên Drive: `reports/metrics/cardd_yolo_model_selection_v1.json`.

## Bước tiếp theo đã khóa

Chạy notebook `CarDD_YOLOv8s_Final_Test_Acc2_v1.ipynb` đúng một lần. Notebook xác minh SHA-256 checkpoint, tạo execution lock trước khi model đọc test và từ chối chạy lại khi report hoặc lock đã tồn tại.

