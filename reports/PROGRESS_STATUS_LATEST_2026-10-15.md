# Báo cáo trạng thái sản phẩm mới nhất

Ngày chốt: 2026-10-15. Phạm vi: Technical PoC / research handoff.

## 1. Sản phẩm hiện là gì?

Sản phẩm là **Claim Review Workbench**: một ứng dụng hỗ trợ nhân viên bảo hiểm nạp hồ sơ, xem hàng đợi ưu tiên, mở ảnh và chứng từ, xem vùng hư hỏng/tín hiệu đối chiếu/quan hệ, xác nhận hoặc sửa kết quả đọc, rồi lưu quyết định có nhật ký. Người dùng thao tác trên một ứng dụng; FastAPI gọi các model local ở phía sau. Hệ thống không gọi LLM bên ngoài để kết luận claim và không tự kết luận gian lận.

## 2. Bằng chứng tích hợp mới nhất

Golden binary integration run ngày 2026-10-15 đã chạy cùng một `claim_id` qua dữ liệu bảng, ảnh PNG, chứng từ PNG, graph và audit:

| Hạng mục | Kết quả |
|---|---|
| XGBoost | completed |
| YOLOv8s-seg | completed; trả 4 vùng hư hỏng trên ảnh tổng hợp |
| DiT → PaddleOCR → LayoutLMv3 | completed; trả 1 document result |
| Consistency rules | completed |
| NetworkX point-in-time graph | completed |
| Media authenticity | completed |
| Review + field correction + audit replay | PASS |
| Trace/model versions | PASS |
| Thời gian analysis trên CPU | 144,7 giây ở lượt chạy v2 gần nhất |

Kết quả này chứng minh luồng kỹ thuật và khả năng truy vết. Vì bằng chứng là dữ liệu tổng hợp, kết quả không được dùng để tuyên bố độ chính xác trên hồ sơ bảo hiểm Việt Nam.

## 3. Model và ý nghĩa nghiệp vụ

| Module | Bằng chứng kỹ thuật hiện tại | Giá trị cho người duyệt | Trạng thái sử dụng |
|---|---|---|---|
| XGBoost | Frozen test AP 0,559; Recall@10% 22,4% | Xếp hồ sơ cần xem trước trong cùng năng lực xử lý | Research; không phải xác suất fraud |
| YOLOv8s-seg | Final mask mAP50–95 0,5140; adapter live | Khoanh vùng nơi cần xem trên ảnh | Research; cần ảnh Việt Nam đúng miền |
| DiT | Independent macro-F1 0,9283 | Chuyển chứng từ vào đúng luồng đọc | Pretrained + independent validation; cần taxonomy Việt Nam |
| PaddleOCR | CER 40,97%; pipeline live | Giảm nhập tay nếu field đủ tin cậy | Baseline yếu; bắt buộc cho sửa/xác nhận |
| LayoutLMv3 | Final field micro-F1 0,8659 | Trích ngày/tổng tiền để đối chiếu | Final test SROIE; chưa phải chứng từ bảo hiểm Việt Nam |
| Rules v2 | Xử lý missing/low-confidence/malformed field | Không biến OCR lỗi thành cảnh báo chắc chắn | Engineering complete; chờ rule-owner sign-off |
| NetworkX v2 | Point-in-time; entity hash; chuẩn hóa phone/plate/shop | Tìm claim dùng chung đầu mối trước thời điểm chấm | Engineering complete; chờ case đã xác minh |
| Media authenticity v3 | Metadata/provenance/reuse/edit traces; pixel gate | Yêu cầu ảnh tốt hơn, giảm cáo buộc sai | Engineering; chưa có universal AI detector |

## 4. Những gì đã hoàn thành

- Một ứng dụng chung cho dashboard, intake, workbench và API docs.
- API live gọi checkpoint thật; model registry lưu version, metric, split và hash.
- Upload ảnh/chứng từ không yêu cầu người dùng nhập JSON kỹ thuật.
- Kết quả có module status, evidence ID, model version, warning và fallback khi thiếu input.
- UI diễn giải theo ba câu: hệ thống thấy gì, vì sao cần quan tâm, nên làm gì tiếp.
- Review/correction lưu vào JSONL audit và mở lại trong lịch sử.
- Golden binary gate chống việc tính nhầm field chuẩn bị trước thành OCR/KIE thật.
- Rules/graph v2 chuẩn hóa format entity và trả `unknown` khi dữ liệu không đủ chắc.
- Dashboard hiển thị roadmap kỹ thuật song song business KPI, gate và blocker.

## 5. Những gì chưa hoàn thành

- Chưa có 20–50 golden claims đúng miền và business sign-off.
- Chưa có validation set chứng từ/ảnh bảo hiểm Việt Nam có consent và ground truth.
- Chưa có S1–S5 được liên kết thật theo `claim_id` để huấn luyện XGBoost candidate mới.
- Chưa có business cost để tính Net Value; KPI Recall@10% 60% không khả thi trên dataset prevalence 24,7% vì trần xấp xỉ 40,5%.
- Pixel AI-image detector chưa được promote; ảnh mất provenance vẫn có thể `inconclusive`.
- Latency CPU 144,7 giây/claim demo còn quá cao cho nghiệp vụ.
- Chưa có authentication/RBAC, database production, encryption/retention, load/security test, monitoring/rollback và UAT.

## 6. Quyết định phát hành hiện tại

**Conditional GO cho Technical PoC và demo nội bộ.** Chưa đạt research handoff vì còn ba xác nhận thủ công: golden multimodal set được ký duyệt, handbook được người ngoài tác giả chạy thử, và đội UI/backend chấp nhận bàn giao. Chưa đủ điều kiện pilot hoặc go-live.

## 7. Thứ tự công việc tiếp theo

1. Thu thập 20–50 claim đã ẩn danh/có quyền dùng và chốt expected action với nghiệp vụ.
2. Đo latency theo từng module, cache kết quả theo evidence hash và chạy worker bất đồng bộ/GPU cho ảnh/chứng từ.
3. Gắn nhãn chứng từ Việt Nam; benchmark OCR preprocessing và field correction rate.
4. Liên kết S1–S5 theo `claim_id`; chọn candidate bằng train/CV/validation rồi dùng external test mới đúng một lần.
5. Gắn mask ảnh hư hỏng đúng miền, ưu tiên `crack`, `dent`, `scratch`; đo useful-region rate.
6. Tạo benchmark authenticity theo source group và chỉ mở pixel detector khi calibration gate đạt.
7. Chạy UAT, security/privacy/load test; chuyển runtime JSON/JSONL sang database và object storage có phân quyền.

Nguồn machine-readable cho dashboard: `configs/model_improvement_status.v1.yaml`. Bằng chứng golden run: `reports/metrics/golden_binary_integration_v1.json`.
