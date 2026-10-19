# 02 — Vận hành, macOS, xử lý lỗi và giới hạn

## Ma trận lệnh

| Việc | Windows | macOS/Linux |
|---|---|---|
| Chạy demo | `python scripts/handoff.py up` | `python3 scripts/handoff.py up` |
| Smoke test | `python scripts/handoff.py smoke` | `python3 scripts/handoff.py smoke` |
| Tạo venv | `py -3.12 -m venv .venv` | `python3.12 -m venv .venv` |
| Python trong venv | `.venv\Scripts\python.exe` | `.venv/bin/python` |
| Activate | `.\.venv\Scripts\Activate.ps1` | `source .venv/bin/activate` |

Docker fixture là đường chạy bàn giao chính vì giảm khác biệt hệ điều hành. Compose dùng `python:3.12-slim` và không mount raw data/artifact vào container.

## Rủi ro riêng trên macOS

1. Chọn đúng Docker Desktop cho Apple chip hoặc Intel chip và bảo đảm Docker engine đã chạy.
2. Không dùng lại `.venv` từ Windows. Virtual environment chứa executable/path phụ thuộc hệ điều hành.
3. macOS không có CUDA. PyTorch có MPS trên phần cứng/hệ điều hành phù hợp, nhưng từng operator/model vẫn phải benchmark; không mặc định tốc độ hoặc kết quả giống CUDA.
4. Paddle/PaddleOCR và một số wheel ảnh có thể chưa có cùng mức hỗ trợ cho mọi Python/architecture. Cài full multimodal theo environment riêng và chỉ công nhận sau readiness + golden smoke.
5. Apple Silicon và Intel là hai kiến trúc khác nhau. Không sao chép native binary/cache giữa hai máy.
6. Giữ line ending LF cho Python/Markdown/YAML. Repo có `.gitattributes` để giảm lỗi CRLF trên macOS.
7. Tên file phân biệt hoa thường trong nhiều môi trường CI/Linux; import và path phải đúng chữ hoa/thường.

## Lỗi thường gặp

### Không mở được `127.0.0.1:8000`

```bash
python scripts/handoff.py preflight
docker compose -f compose.yaml ps
docker compose -f compose.yaml logs --tail 100 claim-review
```

Nếu Docker engine tắt, mở Docker Desktop rồi chạy lại. Nếu port 8000 bận, dừng tiến trình/container cũ hoặc đổi port host trong Compose; không chạy hai server trên cùng port.

### Phân tích chạy lâu

UI gọi analysis job bất đồng bộ. Xem `GET /system/operations`, `GET /analysis-jobs` và trạng thái stage. OCR/document model là phần nặng; cache theo SHA-256/model version giúp lượt sau nhanh hơn. Bản local chỉ dùng một worker để tránh tranh chấp RAM/GPU. Pilot nhiều người dùng cần durable queue, worker riêng, database và object storage.

### Model hiện `unavailable`

Đọc `/readiness` và `module_status.reason`. Kiểm tra artifact path, hash, dependency và biến môi trường. Không biến `unavailable` thành `completed`, không tạo output giả và không dùng kết quả precomputed như bằng chứng model vừa chạy.

### Dashboard/JS lỗi sau khi cập nhật

Hard refresh một lần (`Ctrl+F5` trên Windows, `Cmd+Shift+R` trên macOS). UI response dùng `Cache-Control: no-store`. Nếu lỗi còn, chạy smoke và xem browser console; không xóa claim data để sửa lỗi cache giao diện.

## Dữ liệu và audit

Live local lưu tại:

```text
runtime/claims/{claim_id}/
runtime/audit/reviews.jsonl
runtime/readiness.json
```

Các file này dành cho research trên một máy và nằm ngoài Git. Không đưa PII, token, raw document, chữ ký hoặc checkpoint riêng tư lên GitHub public. Production/pilot cần authentication, RBAC, database transaction, object storage, encryption, backup, retention và audit bất biến.

## Giới hạn model phải trình bày rõ

- XGBoost AP `0,559` chỉ cho biết chất lượng xếp hạng trên frozen test; score không phải xác suất fraud.
- YOLO mask mAP50–95 `0,5140` đo mức phát hiện và độ khớp vùng với nhãn người gán trên test; các lớp `crack/dent/scratch` còn yếu và cần người xác nhận.
- PaddleOCR CER `40,97%` còn yếu trên benchmark hiện tại; bắt buộc cho người dùng xem bản gốc và sửa field.
- LayoutLMv3 Field F1 `0,8659` là trên SROIE, chưa chứng minh cho chứng từ bảo hiểm Việt Nam.
- DiT dùng pretrained checkpoint và taxonomy tài liệu chung; cần validation đúng taxonomy Việt Nam.
- Graph cho thấy đầu mối dùng chung trước thời điểm chấm; liên kết có thể hợp lệ và không tự chứng minh gian lận.
- Authenticity có thể xác nhận provenance/marker khi tồn tại và phát hiện reuse/edit traces. Ảnh bị xóa metadata hoặc tạo bởi công cụ mới có thể lọt, nên kết quả âm tính là `inconclusive`, không phải “ảnh thật”.

## Definition of Done và release

Trạng thái cho phép: **Technical PoC / handoff candidate**. Không ghi “production ready”. Gói `FINAL` chỉ được tạo khi `research_handoff` PASS; script packaging từ chối `final` nếu gate chưa đạt.

Checklist người nhận ký:

- [ ] Clone sạch và chạy `handoff.py up` thành công.
- [ ] `/`, `/dashboard`, `/intake`, `/docs` mở được.
- [ ] Tạo claim, upload, analysis job, review/correction và audit hoạt động theo scope đã chọn.
- [ ] `/readiness` khớp artifact thực tế trên máy.
- [ ] OpenAPI được đội UI chấp nhận.
- [ ] Một người không viết hệ thống chạy lại handbook.
- [ ] Không có secret/PII/raw private data trong Git hoặc ZIP.
- [ ] Các giới hạn model và gate pilot được trình bày trong buổi bàn giao.

## Tài liệu nền tảng chính thức

- Docker Desktop cho Mac: https://docs.docker.com/desktop/setup/install/mac-install/
- Python virtual environment: https://docs.python.org/3/tutorial/venv.html
- PyTorch MPS trên macOS: https://docs.pytorch.org/docs/stable/notes/mps.html
- PaddlePaddle build trên macOS: https://www.paddlepaddle.org.cn/documentation/docs/en/install/compile/macos-compile-make.html
