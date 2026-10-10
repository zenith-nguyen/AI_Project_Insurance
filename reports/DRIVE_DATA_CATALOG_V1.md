# Mục lục dữ liệu Google Drive v1

Project root trên Colab:

```text
/content/drive/MyDrive/AI_Project_Insurance_Acc 2
```

Thư mục tương ứng trong giao diện Google Drive: **My Drive → AI_Project_Insurance_Acc 2**.

## Registry và kiểm toán

| Nội dung | Đường dẫn từ project root |
|---|---|
| Registry toàn bộ nguồn | `data/registry/documents/document_sources_registry.json` |
| Lịch sử các lần intake | `data/registry/documents/intake_runs/` |
| Danh sách 8 cặp SROIE leakage | `data/registry/documents/remediation/sroie_source_split_dedup_v1.json` |
| Audit JSON | `reports/data_audit/documents/document_data_audit_v1.json` |
| Audit Markdown | `reports/data_audit/documents/DOCUMENT_DATA_AUDIT_V1.md` |
| Báo cáo processed SROIE | `reports/data_audit/documents/sroie_processed_split_v1.json` |

## Dữ liệu Bronze nguyên gốc

| Dataset | Vị trí |
|---|---|
| CORD v2 | `data/bronze/documents/cord_v2/v2/` |
| FUNSD | `data/bronze/documents/funsd/original_2019/` |
| FUNSD canonical extracted | `data/bronze/documents/funsd/original_2019/raw/extracted/dataset/` |
| XFUND | `data/bronze/documents/xfund/v1.0/` |
| SROIE | `data/bronze/documents/sroie/ICDAR2019/` |
| RVL-CDIP sample | `data/bronze/documents/rvl_cdip/mirror_main/` |
| MIDV-500 registry/raw metadata | `data/bronze/documents/midv500/v1/` |
| MIDV-2020 registry/raw metadata | `data/bronze/documents/midv2020/v1/` |

Không xóa hoặc sửa file trực tiếp trong `data/bronze/`. Hai cây FUNSD hoàn chỉnh được audit ghi nhận; pipeline dùng cây canonical ở `raw/extracted/dataset`.

## Dữ liệu Processed

Sau khi notebook SROIE Processed PASS:

```text
data/processed/documents/sroie/v1/
├── train.parquet       # 525 rows
├── validation.parquet  # 93 rows
└── test.parquet        # 361 rows
```

Split được tạo theo nhóm SHA-256 ảnh để exact duplicate không thể nằm ở hai split khác nhau.

## Model và kết quả CarDD

| Nội dung | Vị trí |
|---|---|
| YOLOv8n baseline | `artifacts/image/cardd_yolov8n_seg_baseline_v2/` |
| YOLOv8s selected model | `artifacts/image/cardd_yolov8s_seg_candidate_v1/` |
| Checkpoint đã khóa | `artifacts/image/cardd_yolov8s_seg_candidate_v1/weights/best.pt` |
| Validation candidate | `artifacts/image/evaluation/cardd_yolov8s_seg_val_candidate_v1/` |
| Final test | `artifacts/image/evaluation/cardd_yolov8s_seg_final_test_v1/` |
| Model selection report | `reports/metrics/cardd_yolo_model_selection_v1.json` |
| Final-test report | `reports/metrics/cardd_yolov8s_seg_final_test_v1.json` |
| Final-test execution lock | `reports/metrics/cardd_yolov8s_seg_final_test_v1.execution.json` |

## Quy tắc tìm dữ liệu

1. Tìm nguồn và trạng thái trong registry trước.
2. Dùng `inventory.path` trong registry thay vì tự ghép đường dẫn khi viết notebook mới.
3. Bronze chỉ đọc; dữ liệu đã sửa/chuẩn hóa đặt trong Processed/Silver/Gold.
4. Model chỉ đọc split đã khóa và ghi output vào `artifacts/` cùng report vào `reports/`.
