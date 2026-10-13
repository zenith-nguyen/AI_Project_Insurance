# 08 — Definition of Done

## “Done” của dự án hiện tại

Mục tiêu khóa là **research handoff**: một Claim Review Workbench có thể chạy và demo end-to-end, dùng checkpoint đã đăng ký, giải thích rõ module nào chạy, lưu được quyết định/correction, và người khác có thể cài đặt bằng tài liệu bàn giao.

Research handoff chỉ PASS khi:

1. XGBoost, YOLO và DiT → PaddleOCR → LayoutLMv3 đều chạy bằng artifact đúng hash trên máy tích hợp.
2. Một golden claim có dữ liệu bảng, ảnh, chứng từ và graph đi xuyên suốt cùng `claim_id`.
3. UI hiển thị risk, evidence, mask/box, trường trích xuất, consistency và quan hệ từ API live.
4. Thiếu modality trả `partial/blocked` đúng contract; không tạo số liệu giả.
5. Review và correction được lưu với reviewer, thời gian, `trace_id`, giá trị cũ/mới và lý do.
6. Test suite, OpenAPI, readiness và artifact integrity đều PASS.
7. Người không viết hệ thống chạy theo handbook thành công.
8. Đội UI và ML/backend xác nhận bàn giao.
9. Gói FINAL gồm tài liệu `00–08`, PDF, contract, registry, checksum và release manifest.

## Chưa đồng nghĩa với production

Sau research handoff, sản phẩm vẫn chưa được tự từ chối claim. Pilot-ready cần thêm dữ liệu bảo hiểm Việt Nam hợp lệ, bằng chứng license/consent, security/privacy review, load test, UAT nghiệp vụ, monitoring và rollback drill.

## Ba mức hoàn thành

| Mức | Ý nghĩa | Dùng để làm gì |
|---|---|---|
| Engineering foundation | Core API, XGBoost, test và tài liệu nền chạy được | Phát triển nội bộ |
| Research handoff | Multimodal live và bàn giao end-to-end PASS | Demo/đánh giá nghiên cứu |
| Pilot ready | Domain, security, load, UAT và vận hành PASS | Pilot có kiểm soát |

Kiểm tra trạng thái:

```powershell
.\.venv\Scripts\python.exe scripts/check_project_done.py `
  --output runtime/project_done.json
```

Script trả exit code thành công khi đạt target `research_handoff`. Có thể dùng `--level engineering_foundation` để kiểm mốc phát triển hiện tại.

