# 00 — Bắt đầu bàn giao tại đây

## Sản phẩm được bàn giao

**Claim Review Workbench** nhận một hồ sơ bồi thường, gom ảnh xe, chứng từ và dữ liệu liên quan dưới cùng `claim_id`, chạy các module local đang sẵn sàng, giải thích điều cần kiểm tra và lưu quyết định của người duyệt. Hệ thống hỗ trợ xếp hàng và kiểm tra bằng chứng; không tự kết luận gian lận hoặc tự từ chối bồi thường.

Một địa chỉ duy nhất dùng cho toàn bộ giao diện:

- `http://127.0.0.1:8000/` — Dashboard, Nạp hồ sơ, Workbench và Nhật ký.
- `http://127.0.0.1:8000/docs` — Swagger dành cho đội kỹ thuật.

## Cách chạy ít thao tác nhất — Windows và macOS

Yêu cầu: Git và Docker Desktop đang chạy. Bản demo fixture không cần raw data, Google Drive, GPU hoặc checkpoint.

```bash
git clone https://github.com/zenith-nguyen/AI_Project_Insurance.git
cd AI_Project_Insurance
python scripts/handoff.py up
```

Trên macOS nếu lệnh `python` không tồn tại, dùng `python3 scripts/handoff.py up`. Script tự build container, đợi API healthy và kiểm tra tám URL chính. Nếu chưa có Python phù hợp, chạy trực tiếp:

```bash
docker compose -f compose.yaml up -d --build
```

Sau đó mở `http://127.0.0.1:8000/`. Kiểm tra lại bất kỳ lúc nào bằng:

```bash
python scripts/handoff.py smoke
```

Dừng ứng dụng mà không xóa dữ liệu/volume:

```bash
python scripts/handoff.py down
```

## Chọn đúng chế độ

| Nhu cầu | Chế độ | Cần gì | Ý nghĩa |
|---|---|---|---|
| Đội UI tích hợp, demo luồng | Fixture Docker | Git + Docker | Dữ liệu mẫu; API contract và UX chạy được |
| Backend chạy risk bảng | Live core | Python env + `bundle.joblib` đúng hash | XGBoost, rules, graph và audit local |
| Demo đủ ảnh/chứng từ | Full multimodal live | Core + YOLO + LayoutLMv3 + PaddleOCR/DiT | Model thật chạy local; cần máy đã kiểm chứng dependency |
| Pilot nghiệp vụ | Chưa phát hành | Dữ liệu có quyền, security/load/UAT | Chỉ mở sau khi mọi gate pilot PASS |

Fixture chứng minh API/UI tích hợp, không chứng minh độ chính xác model live. Full multimodal live trên máy tích hợp hiện có artifact hợp lệ; người nhận vẫn phải chạy readiness và golden smoke trên chính máy của họ.

## Kiểm tra trước khi bàn giao

```bash
python scripts/handoff.py preflight
python scripts/check_project_done.py --level engineering_foundation --no-fail
python scripts/check_project_done.py --level research_handoff --no-fail
```

Kết quả `engineering_foundation: PASS` cho phép phát triển/demo nội bộ. `research_handoff` chỉ PASS sau ba xác nhận thủ công: golden multimodal run được ký, một người không viết hệ thống chạy handbook thành công, và đội UI/backend chấp nhận bàn giao. `pilot_ready` còn cần dữ liệu Việt Nam hợp lệ, privacy/security, load test, UAT, monitoring và rollback.

## Ba file cần đọc

1. `00_START_HERE.md` — chạy sản phẩm và xác định đúng phạm vi.
2. `01_API_AND_MODEL_INTEGRATION.md` — đội UI/backend và ML nối hệ thống.
3. `02_OPERATIONS_MACOS_AND_LIMITS.md` — vận hành, macOS, lỗi thường gặp và giới hạn.

Gói bàn giao còn có OpenAPI, model registry và một HTML UI mẫu. Checksum trong `SHA256SUMS.txt` dùng để phát hiện file bị thay đổi sau khi đóng gói.

Trạng thái kiểm tra mới nhất trong repo: `reports/HANDOFF_READINESS_2026-10-20.md`.
