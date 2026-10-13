# 07 — Release, security và UAT

Chỉ gắn nhãn `FINAL` cho gói bàn giao khi toàn bộ gate bắt buộc đạt:

- test suite và OpenAPI export PASS;
- artifact hash PASS và multimodal readiness theo scope release;
- không có secret/PII/raw restricted data trong ZIP;
- authentication, authorization, upload isolation và audit retention đã kiểm;
- latency/load test có ngưỡng chấp nhận;
- domain validation trên dữ liệu bảo hiểm Việt Nam;
- UAT với reviewer nghiệp vụ;
- monitoring, incident response và rollback được diễn tập;
- license/consent cho dataset và model được lưu bằng chứng.

Gói `DRAFT` dùng cho phát triển và demo. Gói `FINAL` là snapshot bất biến gồm handbook đánh số, PDF, OpenAPI, client, model registry, checksum và release manifest.

Tạo gói:

```powershell
.\.venv\Scripts\python.exe scripts/build_handoff_bundle.py --status draft
```

Khi đủ release gate, owner mới chạy `--status final --release-version <version>`.

