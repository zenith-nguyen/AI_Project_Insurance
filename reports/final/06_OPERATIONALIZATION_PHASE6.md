# Task 6 - Operationalization Phase 6

Đến ngày 24/10/2026, nhóm đã có một phần luồng nghiên cứu có thể chạy và kiểm tra. FastAPI, Docker Compose ở chế độ dữ liệu mẫu và giao diện HTML cho người duyệt đã có từ trước. Lần bàn giao này bổ sung các phần dưới đây vào mã hiện hành. Nhóm chưa có đầy đủ checkpoint và quyền truy cập để xác nhận toàn bộ luồng live chạy được trên một máy hoặc container khác.

## Phần đã thực hiện trong lần bàn giao

- `POST /verify` nhận `claim_id` và đối số phân tích tùy chọn; dùng chính `SERVICE.analyze()`, trả `risk_score`/`research_risk_score`, `analysis_status`, `model_version`, `evidence_refs`, `trace_id`, `action`, `reasons`, `human_review_required=true`, `mode`, `risk_score_is_probability=false`. OpenAPI snapshot đã xuất lại tại `contracts/claim_review_openapi.v1.json`.
- `src/api/verify.py`: thiếu điểm, partial/blocked hoặc thiếu evidence → `SUPPLEMENT`; tín hiệu tabular risk high (trong live adapter được suy từ score ≥ t2 của bundle) hoặc signal high → `SIU`; risk review (score ≥ t1, < t2) hoặc signal review → `SUPPLEMENT`; chỉ khi complete, không cờ → `STP` (tiếp tục xử lý thông thường dưới giám sát). Reason cho t1/t2 chỉ xuất hiện khi `tabular-priority` có thật; fixture luôn nêu rõ demo. Không ra lệnh chi trả/bác hồ sơ. Chưa thêm field `as_of` tự do vì API chưa chứng minh được mọi feature ở thời điểm đó; intake/scored_at trong store phải được audit trước live.
- `scripts/fairness_audit_phase5.py` nhận file `val_fs` và dự đoán B2 khóa, kiểm tra `claim_id`/nhãn, xuất thống kê nhóm của hàng đợi chung. Không đưa dữ liệu cá nhân lên API công khai.
- Middleware ghi JSON metadata (`trace_id`, method, route, status, thời gian) ra stdout; `src/api/operations_log.py` ghi thêm JSONL theo `claim_id`/action/latency ở `runtime/audit/verify.jsonl`. Không ghi request body, raw evidence, feature hay tên người. Response có `X-Trace-ID`; production cần auth, log retention, truy cập và redaction theo policy.
- `prototype/monitor_dashboard.py` là Streamlit tùy chọn trong profile Compose `monitor`, chỉ bind 127.0.0.1:8501, đọc volume log ở chế độ read-only; hiển thị tỷ lệ STP/SUPPLEMENT/SIU và p95 latency, tách fixture/live, không hiển thị claim_id.
- GitHub Actions `api-research.yml` kiểm tra lint, test contract, build Docker API và smoke `/health`/`verify`; chưa quan sát runner remote. Test cục bộ: `python -m pytest -q tests/test_verify.py tests/test_claim_review_api.py tests/test_openapi_contract.py tests/test_metrics.py`.

Để thử với dữ liệu mẫu, cài `requirements-api.txt`, chạy `INSURANCE_API_MODE=fixture python -m uvicorn src.api.app:app --reload`, rồi gửi `curl -X POST http://127.0.0.1:8000/verify -H 'Content-Type: application/json' -d '{"claim_id":"CLM-DEMO"}'`. Dashboard cục bộ chạy bằng `docker compose --profile monitor up --build` tại `http://127.0.0.1:8501`. Phản hồi ở chế độ này chỉ là demo; các module chưa được kiểm tra trên một hồ sơ thật có cùng `claim_id`. Dashboard cần có xác thực trước khi mở ra mạng. Trên checkout hiện tại, `python scripts/check_live_readiness.py` trả `core_live_ready=false` và `multimodal_live_ready=false`: còn thiếu bundle tabular, checkpoint CarDD/KIE và các phụ thuộc GPU, chứng từ. Artifact trên máy tích hợp của nhóm không có trong bản clone này.

## Backlog với chốt nghiệm thu

| Hạng mục tài liệu task | Tình trạng hiện tại | Điều kiện nghiệm thu tiếp theo |
|---|---|---|
| Tách module services | Monolith có module adapters và readiness; chưa tách service | Contract có version, timeout/circuit breaker, error isolation, tracing từng module; integration test bằng claim thật |
| ONNX CPU | Chưa export và chưa xác nhận parity | Export từng model phù hợp, benchmark sai khác score/metric, CPU latency p95 và tương thích preprocessing |
| CI + Docker smoke | Workflow đã viết, chưa có kết quả runner từ remote | Xem run trên branch, xử lý lỗi môi trường và giữ gate PR |
| Structured JSON logs | `/verify` có log claim ID/action/latency và middleware metadata; chưa phủ mọi route/kho tập trung | Liên kết trace nghiệp vụ, mask PII, log shipping và lưu giữ theo chính sách |
| Streamlit dashboard | Có bản local chỉ đọc log, chưa UAT/performance/security | Xác nhận KPI với Nhật Quyên, auth trước khi truy cập từ mạng |
| Security, PII, auth, storage | Runtime file store nghiên cứu | Authentication/RBAC, mã hóa, consent, retention, backup/restore, audit bất biến, threat test |
| UAT | Chưa có nghiệp vụ/đối tượng thật | Reviewer xác nhận reasons, false positives, escalation, chỉnh sửa và khiếu nại |

Trước khi chạy với dữ liệu thật, cần kiểm tra hơn việc endpoint trả HTTP 200. `INSURANCE_API_MODE=live` cần model artifact và dữ liệu tương ứng. Danh mục tài sản, người chịu trách nhiệm, SLA, nguồn dữ liệu, quyền sử dụng và phép đánh giá độc lập là các điều kiện được nêu trong Task 1, 2 và 7.
