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
```

Ba trường UI phải đọc trước là `analysis_status`, `research_risk_score` và `module_status`. UI phải hiển thị `warnings`, không đổi risk score thành xác suất gian lận.

Endpoint nội dung bằng chứng:

```text
GET /claims/{claim_id}/evidence/{evidence_id}/content
```

UI dùng endpoint này để hiển thị ảnh gốc cùng mask/box. Server chỉ trả file đã có trong manifest của claim và không nhận đường dẫn filesystem từ client.

Contract chuẩn nằm tại `contracts/claim_review_openapi.v1.json`. Hướng dẫn chi tiết nằm tại `reports/API_HANDOFF_GUIDE_2026-10-13.md`.

