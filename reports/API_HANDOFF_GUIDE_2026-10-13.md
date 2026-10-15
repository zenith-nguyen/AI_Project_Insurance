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
let job = await api.startAnalysisJob("CLM-001");
while (["queued", "running"].includes(job.status)) {
  await new Promise(resolve => setTimeout(resolve, 1000));
  job = await api.getAnalysisJob("CLM-001", job.job_id);
}
if (job.status === "failed") throw new Error(job.error);
const analysis = await api.getAnalysis("CLM-001");
await api.saveReview("CLM-001", reviewPayload);
```

Phân tích dùng job nền vì YOLO, OCR và LayoutLMv3 có thể mất vài phút trên CPU. UI hiển thị `job.stage`, `job.message` và `job.elapsed_seconds`; người dùng có thể mở Dashboard trong lúc job vẫn chạy. Nếu hồ sơ, bằng chứng và checkpoint không đổi, backend dùng lại kết quả đã lưu. Thêm tệp mới tự làm cache hết hiệu lực.

UI phải đọc ba trường đầu tiên trước:

- `analysis_status`: `complete`, `partial` hoặc `blocked`;
- `research_risk_score`: có thể `null` nếu thiếu feature bảng;
- `module_status`: lý do module hoàn thành, thiếu input, thiếu artifact hoặc lỗi.

Riêng `module_status.tabular_risk`, dùng `required_field_count`, `provided_field_count`, `missing_field_count` và `missing_business_groups` để giải thích trạng thái chưa chấm. `missing_fields` là chi tiết kỹ thuật, không đưa thẳng cho người nộp hồ sơ. Các mã `claim-intake`, `vehicle_image`, `claim_document` trong `missing_evidence` phải được UI đổi thành tên nghiệp vụ. Chỉ tín hiệu có severity `review` hoặc `high` được đếm là cờ; `info` không phải cờ cần xử lý.

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

Phiên hết hạn sau 10 phút. Dùng khi ảnh cũ, ảnh trùng hoặc nguồn gốc chưa rõ: server phát ba yêu cầu góc chụp, gắn từng ảnh với session, step, thời gian và hash. `guided_unverified` có nghĩa server nhận đủ ảnh theo phiên/bước; chưa phải device attestation, bằng chứng camera có chữ ký hoặc kết luận hiện trường thật.

## Endpoint theo vai trò

| Endpoint | UI chính | Dev/audit | Ý nghĩa |
|---|---:|---:|---|
| `GET /health` | Có | Có | API đang chạy ở fixture hay live |
| `GET /readiness` | Không bắt buộc | Có | Module/checkpoint nào đang hoạt động |
| `GET /version` | Có | Có | Phiên bản model và metric công khai |
| `POST /claims/{id}/intake` | Có | Có | Tạo hồ sơ |
| `POST /claims/{id}/capture-sessions` | Tùy chọn | Có | Tạo phiên chụp hướng dẫn |
| `POST /claims/{id}/evidence` | Có | Có | Tải ảnh hoặc chứng từ |
| `GET /claims/{id}/evidence/{evidence_id}/content` | Có | Có | Hiển thị file đã đăng ký để overlay mask/box |
| `POST /claims/{id}/analysis-jobs` | Có | Có | Khởi động phân tích nền; không giữ request trình duyệt |
| `GET /claims/{id}/analysis-jobs/{job_id}` | Có | Có | Đọc trạng thái/giai đoạn/thời gian job |
| `GET /analysis-jobs` | Dashboard | Có | Liệt kê job gần đây và hồ sơ đang chạy |
| `POST /claims/{id}/analyze` | Không ưu tiên | Có | Endpoint đồng bộ tương thích cũ/debug |
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

UI không gửi đường dẫn máy local cho endpoint nội dung. API chỉ stream file đã đăng ký trong evidence manifest của đúng `claim_id`.

## Nạp bộ 27 hồ sơ demo

Bộ đã chuẩn hóa nằm ngoài Git để không đưa ảnh/PDF vào source control. Dùng importer thay vì nhập JSON kỹ thuật trên UI:

```powershell
.\.venv\Scripts\python.exe scripts\import_demo27_case.py `
  --pack "D:\My Dowload\00_DEMO27_NORMALIZED_2026-10-16_v1" `
  --case CLM-07-P `
  --seed-history `
  --documents minimal `
  --analyze
```

- `minimal`: một hoặc nhiều ảnh xe và một báo giá đã render, phù hợp demo nhanh.
- `full`: toàn bộ nhóm chứng từ đã khử đường dẫn trùng, phù hợp test pipeline nhưng chậm hơn.
- `none`: không tải chứng từ; chỉ dùng để cô lập test ảnh/graph, không dùng cho demo end-to-end.
- `--seed-history`: chỉ dùng khi case có lịch sử riêng như SC02/SC07; reference claim được tạo trước target theo `scored_at`.
- SC07 nguồn có reference nằm sau target. Importer phản chiếu các khoảng thời gian này về trước target để kiểm thử point-in-time mà không cho graph nhìn tương lai; receipt lưu timestamp gốc và timestamp đã import.
- Receipt được ghi vào `run_receipts/`, chứa ID runtime, evidence hash, expected route và actual summary.

Không nhập đồng thời toàn bộ 27 case vào cùng kho runtime để test ảnh trùng. Nhiều case cố ý dùng chung ảnh nguồn; chạy chung sẽ tạo cảnh báo cross-claim ngoài phạm vi expected của từng case.
