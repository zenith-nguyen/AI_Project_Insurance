# Handoff readiness — 2026-10-20

## Quyết định hiện tại

**GO cho Technical PoC/demo nội bộ và bàn giao candidate.** Chưa gắn nhãn `FINAL`, `pilot-ready` hoặc `production-ready`.

## Bằng chứng đã kiểm tra lại

| Hạng mục | Kết quả | Bằng chứng |
|---|---|---|
| Full test suite | PASS | 159 passed, 1 skipped |
| Docker fixture build/start | PASS | `python scripts/handoff.py up` |
| Smoke UI/API | PASS | 8/8 URL gồm health, readiness, version, model evidence, improvement, operations, docs và `/` |
| OpenAPI đồng bộ code | PASS | 22/22 route; đã bổ sung baselines, document policies và operations |
| Engineering foundation DoD | PASS | automated + manual checks của mức foundation đều đạt |
| Live artifact readiness trên máy tích hợp | PASS | XGBoost, YOLO và LayoutLMv3 artifact đúng hash; dependency ready |
| Golden binary integration gần nhất | PASS | Cùng `claim_id`, sáu module completed, image/document binary đi tới analysis, audit replay PASS |
| Research handoff DoD | Chờ ký | Automated ready; còn ba manual gate |

Golden binary run dùng dữ liệu tổng hợp và không cho phép suy ra accuracy trên bảo hiểm Việt Nam. Thời gian analysis CPU đã ghi nhận khoảng 144,7 giây ở run gần nhất; đây là blocker hiệu năng cho pilot, không cản demo kỹ thuật có kiểm soát.

## Ba manual gate còn lại

1. `golden_multimodal_run_signed_off`: chủ nhiệm/nhóm xác nhận bằng chứng golden run.
2. `handbook_reviewed_by_non_author`: một thành viên không viết hệ thống clone sạch và chạy theo guide.
3. `ui_backend_handoff_accepted`: đội UI/backend xác nhận OpenAPI và luồng lỗi/partial.

Ba gate này không thể tự động tick bằng code. Sau khi có bằng chứng và người chịu trách nhiệm ký, cập nhật `configs/project_definition_of_done_v1.yaml`, chạy lại `scripts/check_project_done.py`, rồi mới tạo gói `--status final --confirm-gates`.

## Các việc còn mở trước pilot

- 20–50 golden claims đúng miền, có quyền dùng và expected action được nghiệp vụ ký.
- Validation ảnh/chứng từ bảo hiểm Việt Nam; OCR handwriting/field correction rate.
- Business KPI/cost và external test mới cho candidate tabular.
- Calibration benchmark media authenticity; kết quả `inconclusive` không được hiển thị thành “ảnh thật”.
- Authentication/RBAC, database/object storage, encryption/retention/backup.
- Load/security/privacy test, UAT, monitoring và rollback drill.
- Benchmark riêng cho deployment target; macOS Apple Silicon chỉ mặc định hỗ trợ fixture Docker cho đến khi full model golden smoke PASS trên máy đó.

## Gói bàn giao

Gói compact chứa bốn tài liệu được đánh số theo thứ tự sử dụng, một PDF hợp nhất, HTML UI mẫu, OpenAPI, model registry, release manifest và SHA-256. File `01_GITHUB_CAI_DAT_VA_CAP_NHAT.md` quy định cách nhận phiên bản mới mà không làm mất code local. Full handbook `00–08` vẫn ở Git để tra cứu sâu nhưng không làm gói compact rối hơn.
