# Gói dữ liệu — Báo cáo tiến độ lần 2

Mở tài liệu theo thứ tự sau để trình bày trực tiếp:

1. `PROGRESS_REPORT_2_PRESENTATION_NOTES_V1.md` — kịch bản trình bày ngắn.
2. `PROGRESS_REPORT_2_READINESS_2026-10-10.md` — mức đáp ứng yêu cầu môn học.
3. `data_audit_report.md`, `DOCUMENT_DATA_AUDIT_STATUS_V1.md` và `DOCUMENT_DATA_AUDIT_RUN_2026-10-11.md` — Data Audit Report và kết quả chạy thật.
4. `data_dictionary.md` — Data Dictionary.
5. `DOCUMENT_DATA_SOURCE_PLAN_V1.md` và `DOCUMENT_SOURCE_LINK_AUDIT_V1.md` — nguồn và provenance.
6. `EXPERIMENT_EVIDENCE_INDEX_V1.md` — nơi tìm từng bằng chứng.
7. `CARDD_MODEL_SELECTION_V1.md` và `CARDD_FINAL_TEST_V1.md` — baseline/evaluation đã hoàn tất.
8. `DOCUMENT_MODEL_BASELINE_PLAN_V1.md` — baseline process cho nhánh chứng từ.
9. `model_selection_matrix.md` — Model Selection Matrix.
10. `metrics_v1.md` — Metrics v1.
11. `risk_register_v2_additions.md` — Risk Register v2.
12. `DRIVE_DATA_CATALOG_V1.md` — vị trí dữ liệu và model trên Google Drive.
13. `SROIE_PROCESSED_SPLIT_DIAGNOSTIC_2026-10-11.md` — nguyên nhân lỗi split và bản sửa group-aware.
14. `GROUND_TRUTH_DEFINITION_V1.md` — định nghĩa ground truth theo task.
15. `DATA_LEAKAGE_CHECK_V1.md` — kết quả leakage và remediation.
16. `DOCUMENT_EDA_SOURCE_ANALYSIS_V1.md` — EDA/phân tích nguồn.
17. `REPORT_REQUIREMENTS_COVERAGE_V1.md` — đối chiếu từng yêu cầu mục 6.2.
18. `PRODUCT_MODEL_AND_USAGE_V1.md` — sản phẩm, model stack và cách đưa model vào sử dụng.
19. `CARDD_PICLAB_CONSENT_ACTION_V1.md` — kế hoạch đóng bằng chứng prior consent.
20. `DOCUMENT_GRAPH_IMPLEMENTATION_V1.md` — code, notebook, trạng thái và cách dùng nhánh document/graph.
21. `SROIE_PROCESSED_SPLIT_RESULT_V1.md` — data gate SROIE đã PASS và không còn cross-split overlap.
22. `DOCUMENT_BASELINE_VALIDATION_V1.md` — metric DiT, PaddleOCR và rule KIE trên validation.
23. `Document_DiT_Independent_Validation_Acc2_v2.ipynb` — kiểm tra DiT trên RVL validation mirror đã pin, tương thích `datasets>=3` và độc lập với sample train intake.
24. `LAYOUTLMV3_ALIGNMENT_REMEDIATION_V1.md` — giải thích data gate 0,1290 và thuật toán căn chỉnh đã sửa trong notebook v3.
25. `Document_LayoutLMv3_Candidate_Acc2_v3.ipynb` — candidate KIE đã chạy; vẫn khóa test và giữ nguyên quy tắc chọn model.
26. `LAYOUTLMV3_CANDIDATE_VALIDATION_V2.md` — kết quả validation, model selection và giới hạn của LayoutLMv3.
26. `LAYER_B_STAGE_RELIABILITY_DICTIONARY_V1.md` — data dictionary theo stage, rubric reliability và feature policy cho đủ 39 cột nguồn.
27. `FRAUD_LABEL_PROVENANCE_V1.md` — cách diễn giải target quan sát và giới hạn label provenance.
28. `DATA_MODEL_SYSTEM_CARD_V2.md` — Data Card, Model Card đa module và kiến trúc hệ thống đã cập nhật.
29. `COLAB_CROSS_ACCOUNT_RUNBOOK_V1.md` — quy trình chạy notebook qua nhiều tài khoản mà vẫn dùng chung artifact.

## Trạng thái cần nói rõ

- CarDD: đã hoàn tất baseline, candidate comparison, model lock và final test đúng một lần.
- Document data: registry, intake và audit tự động đã hoàn tất; SROIE raw có tám cặp leakage đã được ghi nhận.
- SROIE processed: PASS với 525/93/361 và exact overlap bằng 0.
- Document baseline: đã có metric cho DiT smoke, PaddleOCR và rule KIE. LayoutLMv3 v3 đạt field micro-F1 0,9214 so với rule 0,6834 và được chọn theo quy tắc khóa trước; SROIE test vẫn khóa. DiT independent validation đang chờ chạy lại bằng notebook v2.
- RAG prompt/retrieval test: chưa áp dụng vì chưa chọn RAG làm baseline.
- Production/go-live: chưa mở; còn cần dữ liệu bảo hiểm thật, PII/license review, API, UI integration, monitoring và UAT.
