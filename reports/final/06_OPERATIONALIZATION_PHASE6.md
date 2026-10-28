# Task 6 - Operationalization Phase 6

Đến ngày 24/10/2026, nhóm đã có một phần luồng nghiên cứu có thể chạy và kiểm tra. FastAPI, Docker Compose ở chế độ dữ liệu mẫu và giao diện HTML cho người duyệt đã có từ trước. Lần bàn giao này bổ sung các phần dưới đây vào mã hiện hành. Nhóm chưa có đầy đủ checkpoint và quyền truy cập để xác nhận toàn bộ luồng live chạy được trên một máy hoặc container khác.

## Phần đã thực hiện trong lần bàn giao

- `POST /verify` nhận `claim_id` và đối số phân tích tùy chọn; dùng chính `SERVICE.analyze()`, trả `risk_score`/`research_risk_score`, `analysis_status`, `model_version`, `evidence_refs`, `trace_id`, `action`, `reasons`, `human_review_required=true`, `mode`, `risk_score_is_probability=false`. OpenAPI snapshot đã xuất lại tại `contracts/claim_review_openapi.v1.json`.
- `src/api/verify.py`: thiếu điểm, partial/blocked hoặc thiếu evidence → `SUPPLEMENT`; tín hiệu tabular risk high (trong live adapter được suy từ score ≥ t2 của bundle) hoặc signal high → `SIU`; risk review (score ≥ t1, < t2) hoặc signal review → `SUPPLEMENT`; chỉ khi complete, không cờ → `STP` (tiếp tục xử lý thông thường dưới giám sát). Reason cho t1/t2 chỉ xuất hiện khi `tabular-priority` có thật; fixture luôn nêu rõ demo. Không ra lệnh chi trả/bác hồ sơ. Chưa thêm field `as_of` tự do vì API chưa chứng minh được mọi feature ở thời điểm đó; intake/scored_at trong store phải được audit trước live.
- `scripts/fairness_audit_phase5.py` nhận file `val_fs` và dự đoán B2 khóa, kiểm tra `claim_id`/nhãn, xuất thống kê nhóm của hàng đợi chung. Không đưa dữ liệu cá nhân lên API công khai.
- Middleware ghi JSON metadata (`trace_id`, method, route, status, thời gian) ra stdout; `src/api/operations_log.py` ghi thêm JSONL theo `claim_id`/action/latency ở `runtime/audit/verify.jsonl`. Không ghi request body, raw evidence, feature hay tên người. Response có `X-Trace-ID`; production cần auth, log retention, truy cập và redaction theo policy.
- `prototype/monitor_dashboard.py` là Streamlit tùy chọn trong profile Compose `monitor`, chỉ bind 127.0.0.1:8501, đọc volume log ở chế độ read-only; hiển thị tỷ lệ STP/SUPPLEMENT/SIU và p95 latency, tách fixture/live, không hiển thị claim_id.
- GitHub Actions `api-research.yml` kiểm tra lint, test contract, build Docker API và smoke `/health`/`verify`; chưa quan sát runner remote. Test cục bộ: `python -m pytest -q tests/test_verify.py tests/test_claim_review_api.py tests/test_openapi_contract.py tests/test_metrics.py`.
- Nhóm chọn thực hiện ONNX cho phần XGBoost tabular. `scripts/export_tabular_onnx.py` chuyển estimator XGBoost sang `tabular_xgboost.onnx`, so điểm thô, điểm sau hiệu chuẩn và hàng đợi trên cùng tập validation; chỉ lưu model cùng `validation.json` khi sai khác điểm không quá 1e-4 và không đổi hàng đợi. Với ma trận one-hot thưa, ô không hiện diện được đưa thành NaN để giữ đúng cách XGBoost hiểu giá trị thiếu. `src/models/onnx_tabular.py` kiểm tra hash bundle/model trước khi nạp, `src/api/live.py` hỗ trợ chọn runtime ONNX khi có cờ cấu hình. Ngày 27/10/2026, `tests/test_export_tabular_onnx.py` chạy qua 1 ca tích hợp trên mô hình tổng hợp và so trực tiếp kết quả adapter cũ với adapter ONNX. Cùng phiên kiểm tra đó, 19 bài test API và metric liên quan cũng đạt. Workflow CI có job riêng cho phép kiểm tra này, chưa quan sát kết quả runner từ xa. Không có `bundle.joblib` đã đăng ký trong bản project này, nên chưa thể xuất và đối chiếu ONNX của model nghiên cứu thật.

Để thử với dữ liệu mẫu, cài `requirements-api.txt`, chạy `INSURANCE_API_MODE=fixture python -m uvicorn src.api.app:app --reload`, rồi gửi `curl -X POST http://127.0.0.1:8000/verify -H 'Content-Type: application/json' -d '{"claim_id":"CLM-DEMO"}'`. Dashboard cục bộ chạy bằng `docker compose --profile monitor up --build` tại `http://127.0.0.1:8501`. Phản hồi ở chế độ này chỉ là demo; các module chưa được kiểm tra trên một hồ sơ thật có cùng `claim_id`. Dashboard cần có xác thực trước khi mở ra mạng. Trên checkout hiện tại, `python scripts/check_live_readiness.py` trả `core_live_ready=false` và `multimodal_live_ready=false`: còn thiếu bundle tabular, checkpoint CarDD/KIE và các phụ thuộc GPU, chứng từ. Artifact trên máy tích hợp của nhóm không có trong bản clone này.

Để xuất ONNX của model thật khi nhóm cung cấp artifact đúng hash, cài `python -m pip install -r requirements-onnx.txt`, rồi chạy từ thư mục gốc project:

```bash
python scripts/export_tabular_onnx.py --bundle artifacts/models/tabular_v1/bundle.joblib --sample data/gold/feature_selection_v1/val_fs.parquet --output-dir artifacts/onnx/tabular_v1
```

Lệnh dừng nếu thiếu cột, model không phải XGBoost hoặc phép đối chiếu không đạt. Tập `val_fs` là dữ liệu validation phục vụ kiểm tra tính tương đương khi chuyển định dạng, không được dùng để nhận một kết quả đánh giá cuối mới. Phần tiền xử lý fit sẵn và calibrator vẫn ở `bundle.joblib`. Sau khi kiểm tra `validation.json` và được nhóm đồng ý thử trên máy có đủ artifact, đặt `INSURANCE_TABULAR_ONNX_DIR=artifacts/onnx/tabular_v1` khi chạy `INSURANCE_API_MODE=live`; mặc định API tiếp tục dùng XGBoost gốc. Nếu hash không khớp thì service từ chối nạp ONNX, không tự chuyển về runtime khác. Muốn triển khai cần thêm kết quả trên bundle thật, đo hiệu năng trên máy đích và đường quay về model cũ.

## Backlog với chốt nghiệm thu

| Hạng mục tài liệu task | Tình trạng hiện tại | Điều kiện nghiệm thu tiếp theo |
|---|---|---|
| Tách module services | Monolith có module adapters và readiness; chưa tách service | Contract có version, timeout/circuit breaker, error isolation, tracing từng module; integration test bằng claim thật |
| ONNX CPU | Có script export XGBoost, parity gate, backend CPU tùy chọn trong API và test tổng hợp; chưa có artifact thật để xuất hoặc chạy live | Nhận bundle đúng hash, chạy trên validation có nguồn gốc, xem `validation.json`, xác nhận độ trễ và đường quay về trước khi quyết định bật runtime ONNX |
| CI + Docker smoke | Workflow đã viết, chưa có kết quả runner từ remote | Xem run trên branch, xử lý lỗi môi trường và giữ gate PR |
| Structured JSON logs | `/verify` có log claim ID/action/latency và middleware metadata; chưa phủ mọi route/kho tập trung | Liên kết trace nghiệp vụ, mask PII, log shipping và lưu giữ theo chính sách |
| Streamlit dashboard | Có bản local chỉ đọc log, chưa UAT/performance/security | Xác nhận KPI với Nhật Quyên, auth trước khi truy cập từ mạng |
| Security, PII, auth, storage | Runtime file store nghiên cứu | Authentication/RBAC, mã hóa, consent, retention, backup/restore, audit bất biến, threat test |
| UAT | Chưa có nghiệp vụ/đối tượng thật | Reviewer xác nhận reasons, false positives, escalation, chỉnh sửa và khiếu nại |

Trước khi chạy với dữ liệu thật, cần kiểm tra hơn việc endpoint trả HTTP 200. `INSURANCE_API_MODE=live` cần model artifact và dữ liệu tương ứng. Danh mục tài sản, người chịu trách nhiệm, SLA, nguồn dữ liệu, quyền sử dụng và phép đánh giá độc lập là các điều kiện được nêu trong Task 1, 2 và 7.
