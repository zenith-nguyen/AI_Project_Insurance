# 01 — Tích hợp API, UI và model

## Luồng sản phẩm

```text
Tạo claim → tải ảnh/chứng từ → chạy analysis job → xem kết quả
→ người duyệt xác nhận/sửa field → lưu quyết định → xem lại nhật ký
```

Người dùng nghiệp vụ không nhập JSON feature. Hệ thống nghiệp vụ/backend map dữ liệu bảng vào `tabular_features`; người dùng chỉ nhập thông tin dễ hiểu và tải file. Khi thiếu feature XGBoost, ảnh/chứng từ và graph vẫn được kiểm tra nếu có, còn điểm hàng đợi hiện “Chưa chấm” cùng nhóm dữ liệu đang thiếu.

## Endpoint chính

| Endpoint | Mục đích nghiệp vụ |
|---|---|
| `POST /claims/{claim_id}/intake` | Tạo hồ sơ và gắn dữ liệu khai báo |
| `POST /claims/{claim_id}/evidence` | Tải ảnh xe hoặc chứng từ |
| `POST /claims/{claim_id}/analysis-jobs` | Chạy phân tích bất đồng bộ, không khóa trình duyệt |
| `GET /claims/{claim_id}/analysis-jobs/{job_id}` | Hiện trạng thái/tiến độ |
| `GET /claims/{claim_id}/analysis` | Lấy kết quả đã hoàn thành |
| `POST /claims/{claim_id}/corrections` | Lưu field người duyệt đã sửa |
| `POST /claims/{claim_id}/review` | Lưu hướng xử lý và lý do |
| `GET /claims/{claim_id}/events` | Đọc lại lịch sử truy vết |
| `GET /claims` | Hàng đợi dashboard |
| `GET /readiness` | Module nào thực sự sẵn sàng |
| `GET /system/model-evidence` | Version, metric, split và hash model |
| `GET /system/operations` | Tải/queue/cache và hướng scale |

Contract đầy đủ nằm trong `04_OPENAPI.json` của gói bàn giao và tại `/docs` khi server chạy.

## Ví dụ tích hợp trình duyệt

Ứng dụng thật dùng `prototype/api-client.js`. Luồng tối thiểu:

```javascript
import { ClaimReviewClient } from "/api-client.js";

const api = new ClaimReviewClient();
await api.createClaim("CLM-DEMO-001", {
  claim_amount: 18500000,
  incident_date: "2026-10-20",
  plate_number: "51A-123.45",
  tabular_features: {},
  relationship_entities: {}
});
await api.uploadEvidence("CLM-DEMO-001", { kind: "image", file: imageFile });
await api.uploadEvidence("CLM-DEMO-001", { kind: "document", file: documentFile });
const job = await api.startAnalysisJob("CLM-DEMO-001");
// Poll job.status đến completed/failed, rồi gọi getAnalysis.
```

Không tự retry upload vì có thể tạo evidence trùng. Khi job chạy lâu, UI tiếp tục poll endpoint job; không gửi thêm analysis job cho cùng claim.

## Cách đọc kết quả

- `analysis_status=complete`: tất cả module cần thiết cho phạm vi đó đã chạy.
- `analysis_status=partial`: có kết quả hữu ích nhưng một hoặc nhiều modality/module thiếu.
- `analysis_status=blocked`: thiếu đầu vào bắt buộc để chấm risk; các kiểm tra độc lập vẫn có thể có kết quả.
- `research_risk_score`: điểm xếp thứ tự hàng đợi, không phải xác suất gian lận.
- `evidence_completeness`: tỷ lệ **loại đầu vào yêu cầu đã nhận**, không phải chất lượng hoặc tính xác thực của bằng chứng.
- `signals`: cờ để người duyệt mở bằng chứng và xác minh; cờ không phải kết luận gian lận.
- `module_status`: nguồn sự thật để UI nói model đã chạy, bị thiếu input, thiếu artifact hay lỗi.
- `warnings`: phải hiển thị cho người duyệt; không được bỏ qua để tạo giao diện “đẹp”.

## Tích hợp model local

Model registry là `configs/model_registry.v1.yaml`. Mỗi module phải có version, task, artifact URI, hash/revision, metric, evaluation split, evidence report và status. Server chỉ bật adapter khi artifact/dependency đúng yêu cầu.

Đường dẫn mặc định:

```text
artifacts/models/tabular_v1/bundle.joblib
artifacts/models/damage_segmentation/cardd_candidate_v1/best.pt
artifacts/models/document_kie/layoutlmv3_sroie_candidate_v2/checkpoint-264/
```

Biến môi trường live:

```text
INSURANCE_API_MODE=live
INSURANCE_YOLO_WEIGHTS=<best.pt>
INSURANCE_LAYOUTLM_CHECKPOINT=<checkpoint-264 directory>
INSURANCE_OCR_LANG=vi
INSURANCE_OCR_PROFILE=robust
INSURANCE_PRELOAD_MODELS=1
```

Windows integration machine có thể dùng `scripts/setup_live.ps1` và `scripts/run_live.ps1`. Với macOS, nên dùng máy Mac cho UI/API fixture; full multimodal live phải tạo Python 3.12 environment riêng, cài từng dependency theo wheel tương thích kiến trúc và chạy readiness/golden smoke. Không copy `.venv` giữa Windows, Intel Mac và Apple Silicon.

Kiểm tra artifact và chạy gate:

```bash
python scripts/check_live_readiness.py --output runtime/readiness.json
python scripts/run_golden_live_smoke.py --require-all
```

Hash sai là lỗi bàn giao, không sửa registry để “cho chạy”. Checkpoint lớn và raw data không đưa vào Git; phát hành qua artifact store có quyền truy cập và manifest hash.

## Chứng minh đây là model của dự án

- XGBoost được train trong pipeline Layer B; bundle, feature schema, metric và split được khóa.
- YOLOv8s-seg được fine-tune trên CarDD; checkpoint và final-test report có hash.
- LayoutLMv3 được fine-tune cho trường `date/total`; checkpoint và final test được khóa.
- DiT và PaddleOCR là pretrained component chạy local, được nhóm benchmark riêng; nhóm không tuyên bố tự train chúng từ đầu.
- Rules và NetworkX là thuật toán Python xác định, không phải LLM.
- Media authenticity dùng provenance/metadata/reuse và forensic gate; không tuyên bố là universal AI-image detector.

Request claim được xử lý trong FastAPI local. Hệ thống không gửi dữ liệu claim cho API LLM bên ngoài.
