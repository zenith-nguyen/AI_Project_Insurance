# CarDD YOLOv8s-seg — Final Test v1

**Ngày xác minh:** 10/10/2026  
**Model:** `yolov8s-seg candidate v1`  
**Protocol:** model khóa bằng validation; test chạy đúng một lần

## Artifact integrity

Tất cả kiểm tra từ notebook read-only đều PASS:

- đúng split `test` và `test_run_number = 1`;
- đúng 419 ảnh và 931 instance;
- model/checkpoint đúng bản đã chọn;
- SHA-256 checkpoint trong report, selection report và file trên Drive khớp;
- model selection không dùng test;
- execution lock ở trạng thái `completed`;
- `run_id` của report và lock khớp;
- SHA-256 final report trong execution lock khớp file;
- đủ sáu lớp và sáu per-class mask metric.

Checkpoint SHA-256:

```text
6c0d828760a427d48623653dcd6fffeb1cf591045d9ce8b8684a1d0f5f89420b
```

## Kết quả tổng

| Metric | Final test |
|---|---:|
| Mask mAP50-95 | **0,513978** |
| Mask mAP50 | **0,681571** |
| Mask mAP75 | **0,519355** |
| Box mAP50-95 | **0,539952** |
| Box mAP50 | **0,685981** |
| Box mAP75 | **0,556786** |

## Kết quả theo lớp

| Lớp | Mask mAP50-95 |
|---|---:|
| crack | 0,086252 |
| dent | 0,277864 |
| glass shatter | 0,917869 |
| lamp broken | 0,670178 |
| scratch | 0,280436 |
| tire flat | 0,851268 |

## So với validation đã dùng để chọn model

- Validation mask mAP50-95: `0,528379`.
- Final-test mask mAP50-95: `0,513978`.
- Chênh lệch: khoảng `-0,0144`.

Khoảng giảm tổng thể không làm thay đổi model selection vì checkpoint đã khóa trước khi mở test. `Tire flat` giảm rõ so với validation, trong khi `glass shatter`, `lamp broken` và `scratch` cao hơn. Đây là bằng chứng cần đưa vào error analysis; không được dùng để chỉnh model theo test.

## Artifact trên Google Drive

```text
/content/drive/MyDrive/AI_Project_Insurance_Acc 2/reports/metrics/cardd_yolov8s_seg_final_test_v1.json
/content/drive/MyDrive/AI_Project_Insurance_Acc 2/reports/metrics/cardd_yolov8s_seg_final_test_v1.execution.json
/content/drive/MyDrive/AI_Project_Insurance_Acc 2/reports/metrics/cardd_yolo_model_selection_v1.json
/content/drive/MyDrive/AI_Project_Insurance_Acc 2/artifacts/image/cardd_yolov8s_seg_candidate_v1/weights/best.pt
```

## Trạng thái

Nhánh CarDD đã hoàn tất training, model selection và evaluation. Không chạy final test lần hai. Việc còn lại ngoài modeling là lưu prior consent theo license và, nếu cần, tạo model card/error gallery từ run hiện có.
