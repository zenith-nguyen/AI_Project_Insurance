# API handoff guide — Claim Review Workbench

## Cách hiểu ngắn nhất

Đội UI chỉ cần dùng một client: `prototype/api-client.js`. Luồng nghiệp vụ thông thường có bốn thao tác:

```text
Tạo claim → tải bằng chứng → phân tích → lưu quyết định
```

Authenticity chạy tự động khi tải ảnh. UI không cần gọi endpoint authenticity riêng trong luồng bình thường.

## Luồng chính cho đội UI

```javascript
import {ClaimReviewClient} from "/api-client.js";

const api = new ClaimReviewClient();
await api.createClaim("CLM-001", claimPayload);
await api.uploadEvidence("CLM-001", {kind: "image", file: imageFile});
await api.uploadEvidence("CLM-001", {kind: "document", file: pdfFile});
const analysis = await api.analyzeClaim("CLM-001");
await api.saveReview("CLM-001", reviewPayload);
```

UI phải đọc ba trường đầu tiên trước:

- `analysis_status`: `complete`, `partial` hoặc `blocked`;
- `research_risk_score`: có thể `null` nếu thiếu feature bảng;
- `module_status`: lý do module hoàn thành, thiếu input, thiếu artifact hoặc lỗi.

## Guided capture

```javascript
const session = await api.startGuidedCapture("CLM-001");
for (const instruction of session.instructions) {
  await api.uploadEvidence("CLM-001", {
    kind: "image",
    file: filesByStep[instruction.step],
    captureSessionId: session.session_id,
    challengeStep: instruction.step,
  });
}
```

Phiên hết hạn sau 10 phút. `guided_unverified` có nghĩa server nhận đủ ảnh theo phiên/bước; chưa phải device attestation hoặc bằng chứng camera có chữ ký.

## Endpoint theo vai trò

| Endpoint | UI chính | Dev/audit | Ý nghĩa |
|---|---:|---:|---|
| `GET /health` | Có | Có | API đang chạy ở fixture hay live |
| `GET /readiness` | Không bắt buộc | Có | Module/checkpoint nào đang hoạt động |
| `GET /version` | Có | Có | Phiên bản model và metric công khai |
| `POST /claims/{id}/intake` | Có | Có | Tạo hồ sơ |
| `POST /claims/{id}/capture-sessions` | Tùy chọn | Có | Tạo phiên chụp hướng dẫn |
| `POST /claims/{id}/evidence` | Có | Có | Tải ảnh hoặc chứng từ |
| `POST /claims/{id}/analyze` | Có | Có | Chạy orchestration tự động |
| `GET /claims/{id}/analysis` | Có | Có | Đọc lại kết quả trong tiến trình hiện tại |
| `POST /claims/{id}/review` | Có | Có | Lưu quyết định và lý do |
| `POST /claims/{id}/corrections` | Có | Có | Lưu sửa OCR/KIE có audit trail |
| `GET .../authenticity` | Không | Có | Đọc chi tiết một ảnh khi điều tra/debug |

## Mã lỗi cần xử lý

| HTTP | UI nên làm gì? |
|---:|---|
| `404` | Kiểm tra claim/evidence đã được tạo hay chưa |
| `409` | Claim đã tồn tại hoặc chưa phân tích trước khi review |
| `422` | Hiển thị `detail`: sai schema, file, phiên chụp hoặc dữ liệu |
| `500` | Hiển thị mã trace nếu có và báo backend; không tự retry upload nhiều lần |

## Trách nhiệm giữa hai nhóm

**ML/backend** quản lý model registry, checkpoint/hash, schema API, inference, audit log và `readiness`.

**UI** chỉ phụ thuộc OpenAPI và `api-client.js`; không đọc trực tiếp checkpoint, Google Drive hoặc file model. UI phải hiện `partial/blocked`, warnings và lý do module thiếu, không đổi risk score thành “xác suất gian lận”.

## Chạy và kiểm tra

```powershell
# UI với fixture, không cần model
docker compose up --build

# Máy ML/backend
powershell -ExecutionPolicy Bypass -File scripts/setup_live.ps1 -ArtifactRoot "D:\shared-model-artifacts"
.\.venv\Scripts\python.exe scripts/check_live_readiness.py --output runtime/readiness.json
powershell -ExecutionPolicy Bypass -File scripts/run_live.ps1
```

Swagger: `http://127.0.0.1:8000/docs`. Contract khóa để sinh client nằm tại `contracts/claim_review_openapi.v1.json`.
