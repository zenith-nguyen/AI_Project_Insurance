# Hướng dẫn onboarding và artifact — 13/10/2026

## Phân công hiện tại

- **Data/backend/ML owner:** quản lý dữ liệu, DVC, checkpoint, model registry, live adapters, final-test protocol và phát hành API.
- **UI team:** dùng fixture API/OpenAPI, phát triển giao diện và gửi review decisions; không cần raw data, GPU hoặc checkpoint.

## UI team: clone và chạy một lệnh

Phương án ít phụ thuộc nhất là Docker Desktop:

```powershell
git clone https://github.com/zenith-nguyen/AI_Project_Insurance.git
cd AI_Project_Insurance
docker compose up --build
```

Mở UI tại `http://127.0.0.1:8000/` và Swagger tại `http://127.0.0.1:8000/docs`. Dừng bằng `Ctrl+C`, sau đó chạy `docker compose down` nếu cần.

Nếu không dùng Docker:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_ui.ps1
powershell -ExecutionPolicy Bypass -File scripts/run_ui.ps1
```

UI hiện gọi fixture API nhưng response schema giống live API. Khi backend live sẵn sàng, UI giữ nguyên endpoint/schema và chỉ đổi API base URL nếu tách deployment.

## Data/backend/ML owner: chuẩn bị DVC remote

Repository hiện có DVC metadata nhưng chưa có remote. Tạo một thư mục riêng trong Google Drive dùng chung, ví dụ `AI_Project_Insurance_DVC_Remote`, rồi lấy folder ID từ URL. Không dùng thư mục project gốc làm DVC remote vì các object cache sẽ làm Drive khó đọc.

Cài hỗ trợ Google Drive và cấu hình remote:

```powershell
.\.venv\Scripts\python.exe -m pip install "dvc[gdrive]"
.\.venv\Scripts\dvc.exe remote add -d team-gdrive gdrive://FOLDER_ID_CUA_DVC_REMOTE
.\.venv\Scripts\dvc.exe push
git add .dvc/config data/bronze/layerB_claims.dvc data/silver/layerB_claims.dvc dvc.yaml dvc.lock
git commit -m "Configure shared DVC remote"
git push
```

Thành viên ML được cấp quyền vào thư mục remote rồi chạy:

```powershell
.\.venv\Scripts\python.exe -m pip install "dvc[gdrive]"
.\.venv\Scripts\dvc.exe pull
```

Chỉ push dữ liệu có quyền chia sẻ. Dataset bị giới hạn license/PII chỉ lưu manifest và hướng dẫn tải; không push raw data đó lên remote chung.

## Artifact và Google Drive

Trong giai đoạn hiện tại, chỉ data/backend/ML owner cần truy cập `AI_Project_Insurance_Acc 2`. UI team không cần Drive.

Giữ một thư mục project duy nhất và tránh tạo nhiều folder cùng tên ở các tài khoản. Cấp quyền Viewer cho người chỉ chạy inference; Editor chỉ dành cho owner chạy protocol. Trong Colab, xác nhận project thật bằng cả đường dẫn MyDrive và shortcut target.

Các artifact chính:

```text
artifacts/image/cardd_yolov8s_seg_candidate_v1/weights/best.pt
artifacts/document/layoutlmv3_sroie_candidate_v2/checkpoint-264/
reports/metrics/documents/layoutlmv3_sroie_candidate_validation_v2.json
```

## Kiểm tra hash trước khi dùng model

Với file checkpoint:

```powershell
.\.venv\Scripts\python.exe scripts/hash_artifact.py PATH_TO_FILE --expected EXPECTED_SHA256
```

Với thư mục checkpoint:

```powershell
.\.venv\Scripts\python.exe scripts/hash_artifact.py PATH_TO_DIRECTORY --expected EXPECTED_TREE_SHA256
```

Hash đang khóa:

```text
YOLOv8s-seg best.pt:
6c0d828760a427d48623653dcd6fffeb1cf591045d9ce8b8684a1d0f5f89420b

LayoutLMv3 checkpoint-264 tree:
2b008c90f764c79be36f7082a96e84ba6d28aaccb512dd801123abe55c1ead3c
```

Nếu hash lệch, không chạy test/inference và không sửa registry. Kiểm tra lại account, shortcut, version và file đồng bộ.

## Trạng thái clone-ready

- UI/API fixture: clone-ready bằng Docker Compose hoặc hai PowerShell scripts.
- Source/tests/reports: clone-ready.
- Full training/live inference: chưa clone-ready cho đến khi DVC remote, model fetch và live adapters hoàn tất.
- UI team không bị phụ thuộc vào tiến độ model live.
