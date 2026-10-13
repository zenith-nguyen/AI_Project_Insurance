# 02 — Cài đặt và chạy nhanh

## Đội UI

Không cần raw data, Google Drive, GPU hoặc checkpoint:

```powershell
git clone https://github.com/zenith-nguyen/AI_Project_Insurance.git
cd AI_Project_Insurance
docker compose up --build
```

Mở `http://127.0.0.1:8000/`; Swagger ở `http://127.0.0.1:8000/docs`.

Không dùng Docker:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_ui.ps1
powershell -ExecutionPolicy Bypass -File scripts/run_ui.ps1
```

## ML/backend live

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_live.ps1 `
  -ArtifactRoot "D:\shared-model-artifacts" `
  -InstallMultimodalDependencies
.\.venv\Scripts\python.exe scripts/check_live_readiness.py `
  --output runtime/readiness.json
powershell -ExecutionPolicy Bypass -File scripts/run_live.ps1
```

`core_live_ready=true` nghĩa nhánh risk bảng chạy được. `multimodal_live_ready=true` chỉ khi XGBoost, YOLO và document pipeline đều có artifact/dependency hợp lệ.

`setup_live.ps1` cũng chạy 5 golden claims qua đúng endpoint API và ghi bằng chứng vào `runtime/core_live_smoke.json`. Dùng `-InstallMultimodalDependencies` trên máy ML/backend có checkpoint; đội UI không cần switch này.

## Demo có ảnh xe và chứng từ giả lập

Sau khi `setup_live.ps1` hoàn thành, chạy một lần:

```powershell
.\.venv\Scripts\python.exe scripts/seed_synthetic_demo.py
powershell -ExecutionPolicy Bypass -File scripts/run_live.ps1
```

Mở `http://127.0.0.1:8000/?claim_id=CLM-DEMO-SYN-001`; tab bằng chứng có đường dẫn `http://127.0.0.1:8000/?claim_id=CLM-DEMO-SYN-001&tab=evidence`. Script tạo một hồ sơ local với ảnh xe AI tạo, giấy sửa xe giả lập và graph giả lập. Khi chạy lại, script từ chối ghi đè một claim không có marker demo. Trường ngày/tiền của chứng từ demo đã chuẩn bị sẵn để thử consistency; đây chưa phải kết quả OCR/KIE. Đội UI chỉ cần URL hoặc API contract, không cần checkpoint.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

