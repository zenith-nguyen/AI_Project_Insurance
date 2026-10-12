# Đối chiếu yêu cầu Báo cáo tiến độ lần 2

| Yêu cầu | Artifact trong gói | Trạng thái |
|---|---|---|
| Data Audit Report | `data_audit_report.md`, `DOCUMENT_DATA_AUDIT_RUN_2026-10-11.md` | Có kết quả thật |
| Data Dictionary / KB Audit | `data_dictionary.md`, `LAYER_B_STAGE_RELIABILITY_DICTIONARY_V1.md`, `layer_b_field_governance_v1.csv` | Có đủ 39 cột; KB/RAG chưa thuộc baseline |
| EDA / phân tích tài liệu nguồn | `DOCUMENT_EDA_SOURCE_ANALYSIS_V1.md`, `DOCUMENT_SOURCE_LINK_AUDIT_V1.md` | Có |
| Ground Truth Definition / Citation Policy | `GROUND_TRUTH_DEFINITION_V1.md` | Có; RAG ghi N/A hiện tại |
| Data Leakage Check | `DATA_LEAKAGE_CHECK_V1.md`, `SROIE_PROCESSED_SPLIT_DIAGNOSTIC_2026-10-11.md` | Có kết quả và remediation |
| Baseline model/process | `CARDD_BASELINE_V2_RESULTS.md`, `DOCUMENT_MODEL_BASELINE_PLAN_V1.md`, `DOCUMENT_GRAPH_IMPLEMENTATION_V1.md` | CarDD hoàn tất; document baseline đã có metric, LayoutLMv3 candidate chờ GPU |
| Model Selection Matrix | `model_selection_matrix.md`, `CARDD_MODEL_SELECTION_V1.md` | Có |
| Metrics v1 | `metrics_v1.md`, `CARDD_FINAL_TEST_V1.md`, `DOCUMENT_BASELINE_VALIDATION_V1.md` | Có CarDD và document baseline validation |
| Risk Register v2 | `risk_register_v2_additions.md` | Có |
| RAG prompt/retrieval test | `GROUND_TRUTH_DEFINITION_V1.md` ghi rõ chưa áp dụng | N/A vì chưa chọn RAG |

## Phạm vi trình bày trung thực

Nhóm có thể tuyên bố CarDD evaluation v1, document data audit, SROIE processed data gate và document baseline validation đã hoàn tất. Không tuyên bố LayoutLMv3 đã train hoặc document pipeline đạt chất lượng production.

Source code cho classifier/OCR/KIE/consistency/NetworkX đã được xây và unit-test. DiT, PaddleOCR và rule KIE đã có validation metric; NetworkX hiện mới có synthetic engineering demo.
