# 03 — API và tích hợp UI

Đội UI import client dùng chung:

```javascript
import {ClaimReviewClient} from "/api-client.js";
const api = new ClaimReviewClient();
```

Luồng chính:

```javascript
await api.createClaim(claimId, claimPayload);
await api.uploadEvidence(claimId, {kind: "image", file: imageFile});
const analysis = await api.analyzeClaim(claimId);
await api.saveReview(claimId, reviewPayload);
const events = await api.getEvents(claimId);
```

Ba trường UI phải đọc trước là `analysis_status`, `research_risk_score` và `module_status`. UI phải hiển thị `warnings`, không đổi risk score thành xác suất gian lận.

Khi `module_status.tabular_risk.status=blocked_missing_input`, backend trả thêm dữ liệu giải thích ổn định để UI không phải tách chuỗi lỗi:

```json
{
  "required_field_count": 29,
  "provided_field_count": 0,
  "missing_field_count": 29,
  "missing_business_groups": ["policy", "customer", "incident", "claim_cost", "vehicle"],
  "missing_fields": ["policy_state", "incident_type"]
}
```

`missing_business_groups` dùng cho giao diện nghiệp vụ; `missing_fields` chỉ đặt trong phần kỹ thuật. `missing_evidence` dùng mã contract, nhưng UI phải ánh xạ sang tên tiếng Việt trước khi hiển thị. `graph_features.query_entity_display` chứa giá trị đối chiếu đã giới hạn lộ lọt: số điện thoại chỉ hiện bốn số cuối.

Endpoint nội dung bằng chứng:

```text
GET /claims/{claim_id}/evidence/{evidence_id}/content
```

UI dùng endpoint này để hiển thị ảnh gốc cùng mask/box. Server chỉ trả file đã có trong manifest của claim và không nhận đường dẫn filesystem từ client.

Contract chuẩn nằm tại `contracts/claim_review_openapi.v1.json`. Hướng dẫn chi tiết nằm tại `reports/API_HANDOFF_GUIDE_2026-10-13.md`.

Trang `/` hiện là Claim Review Workbench v3. Team UI có thể xem demo với `?claim_id=CLM-DEMO-SYN-001` và dùng cùng `prototype/api-client.js` để tích hợp giao diện riêng. `module_status.document_pipeline.status=completed_precomputed` nghĩa là có trường chứng từ chuẩn bị sẵn; file upload chưa được OCR/KIE đọc. Chỉ `completed` mới là module đã chạy thật. `GET /claims/{claim_id}/events` đọc lại review và correction đã lưu để hiển thị nhật ký; bản demo local chưa có xác thực người dùng, vì vậy không đưa endpoint này lên môi trường công khai.

## Dashboard và bằng chứng kỹ thuật

```text
GET /claims
GET /system/model-evidence
```

`GET /claims` cấp dữ liệu cho `/dashboard`: điểm xếp hạng, số loại đầu vào, cờ theo mức độ, quyết định gần nhất và số sự kiện audit. `GET /system/model-evidence` công bố chế độ xử lý, trạng thái module, phiên bản, SHA-256, metric và nguồn huấn luyện. Endpoint này giúp người trình bày chứng minh request được xử lý bằng artifact cục bộ và không gửi hồ sơ sang LLM bên ngoài.

Các đường dẫn lưu local trong bản research:

```text
runtime/claims/{claim_id}/claim.json
runtime/claims/{claim_id}/evidence_manifest.json
runtime/claims/{claim_id}/analysis.json
runtime/claims/{claim_id}/vehicle_images/
runtime/claims/{claim_id}/documents/
runtime/audit/reviews.jsonl
```

Đây là lưu trữ demo một máy. Trước pilot nhiều người dùng cần database, object storage, đăng nhập/phân quyền, backup và chính sách lưu/xóa dữ liệu.

