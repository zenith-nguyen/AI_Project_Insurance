# Experiment Evidence Index v1

## Nhánh CarDD đã đóng

| Bằng chứng | Artifact |
|---|---|
| Baseline YOLOv8n-seg | `CARDD_BASELINE_V2_RESULTS.md` |
| Candidate và quy tắc chọn model | `CARDD_MODEL_SELECTION_V1.md` |
| Final test đúng một lần | `CARDD_FINAL_TEST_V1.md` |
| Checkpoint đã khóa | `artifacts/image/cardd_yolov8s_seg_candidate_v1/weights/best.pt` |
| Checkpoint SHA-256 | `6c0d828760a427d48623653dcd6fffeb1cf591045d9ce8b8684a1d0f5f89420b` |
| Final mask mAP50-95 | `0.5139777577` trên 419 ảnh, 931 instances |

## Nhánh chứng từ đang thực hiện

| Bằng chứng | Artifact |
|---|---|
| Registry nguồn | `data/registry/documents/document_sources_registry.json` |
| Intake run | `data/registry/documents/intake_runs/*.json` |
| Audit notebook | `Document_Data_Audit_Acc2_v1.ipynb` |
| SROIE leakage remediation | `data/registry/documents/remediation/sroie_source_split_dedup_v1.json` |
| Processed split notebook | `Document_SROIE_Processed_Split_Acc2_v1.ipynb` |
| Model/baseline protocol | `DOCUMENT_MODEL_BASELINE_PLAN_V1.md` |
| Data operations | `DOCUMENT_DATA_OPERATIONS_GUIDE_V1.md` |
| Claim integration contract | `DOCUMENT_CLAIM_INTEGRATION_CONTRACT_V1.md` |

## Tiêu chuẩn bằng chứng cho lần báo cáo sau

Mỗi thí nghiệm phải lưu dataset revision/checksum, split manifest, seed, package version, config, metric theo lớp/trường, error analysis, checkpoint SHA-256 và quy tắc model selection. Final test chỉ chạy sau khi model được khóa bằng validation.
