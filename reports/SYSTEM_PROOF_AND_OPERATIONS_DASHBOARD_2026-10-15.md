# System proof and operations dashboard

Ngày cập nhật: 2026-10-15.

## Dashboard quản lý

Mở duy nhất `http://127.0.0.1:8000/` để vào sản phẩm. Trang đầu là dashboard; dùng menu trong ứng dụng để chuyển sang nạp hồ sơ, workbench và lịch sử. Dashboard mặc định xếp **ưu tiên cao → cần rà soát → thông thường → chưa phân tích**, và trong mỗi nhóm hiển thị hồ sơ mới trước.

Mỗi dòng giải thích riêng:

- lý do hồ sơ được ưu tiên;
- điểm XGBoost nếu đủ feature bảng;
- số loại đầu vào đã nhận trên tổng số loại yêu cầu;
- số file thực tế đã upload;
- số cờ mức `high` và `review`;
- quyết định gần nhất, người lưu và thời gian;
- nút mở Workbench hoặc mở thẳng tab Lịch sử.

`3/3 loại đầu vào` chỉ có nghĩa hệ thống nhận đủ các nhóm dữ liệu được yêu cầu. Nó không phải accuracy, confidence hoặc bằng chứng rằng nội dung file đúng.

## Dữ liệu được lưu ở đâu

Trong bản research local:

```text
runtime/claims/{claim_id}/claim.json
runtime/claims/{claim_id}/evidence_manifest.json
runtime/claims/{claim_id}/vehicle_images/
runtime/claims/{claim_id}/documents/
runtime/claims/{claim_id}/authenticity/
runtime/claims/{claim_id}/analysis.json
runtime/audit/reviews.jsonl
```

`reviews.jsonl` lưu cả review decision và field correction với `claim_id`, `trace_id`, reviewer, thời gian và lý do. Dashboard đọc lại dữ liệu này sau restart. Đây là research storage; pilot phải dùng database/object storage có authentication, RBAC, encryption, backup và retention policy.

## Chứng minh không gọi LLM bên ngoài

Endpoint `GET /system/model-evidence` công bố:

- `external_llm_api_used: false`;
- `claim_data_sent_to_external_llm: false`;
- model version, implementation, checkpoint SHA-256, metric, evaluation split và trạng thái;
- readiness của adapter local;
- đường dẫn lưu claim và audit log.

Model chạy trong sản phẩm:

| Module | Bản chất |
|---|---|
| XGBoost | Train trong dự án để xếp hạng rủi ro bảng |
| YOLOv8s-seg | Fine-tune trong dự án trên CarDD để phân đoạn hư hỏng |
| DiT | Checkpoint pretrained, dự án đánh giá độc lập |
| PaddleOCR | Engine pretrained, dự án benchmark trên validation |
| LayoutLMv3 | Fine-tune trong dự án trên SROIE sạch |
| Consistency rules | Luật Python xác định, không train |
| NetworkX | Feature graph theo thời điểm, không train |
| Media authenticity | Provenance/metadata/hash local; pixel detector vẫn khóa đến khi domain calibration PASS |

Bằng chứng trình bày gồm model registry, hash artifact, báo cáo final test, source adapter, test suite và `/readiness`. Download checkpoint từ Hugging Face/Drive là bước phân phối artifact; inference claim sau đó chạy local và không phải gọi API LLM.

## Giới hạn detector ảnh AI

Module hiện phát hiện tốt trường hợp có C2PA/metadata khai báo, phần mềm chỉnh sửa và ảnh trùng/gần trùng. Nó chưa có pixel detector được hiệu chuẩn trên ảnh bảo hiểm Việt Nam. Vì vậy ảnh AI không marker phải trả `inconclusive`. Adapter calibrated pixel-forensics đã có trong code nhưng chỉ kích hoạt sau khi benchmark đúng miền tạo threshold và calibration manifest hợp lệ.

## Kịch bản trình bày 90 giây

1. Mở `/dashboard`, chỉ vào hàng đợi: hồ sơ được xếp theo cờ cần xử lý; điểm XGBoost và mức đủ đầu vào là hai khái niệm khác nhau.
2. Mở `CLM-DEMO-SYN-001`, chỉ vùng YOLO khoanh, trường chứng từ, tín hiệu không khớp và quan hệ dùng chung.
3. Lưu một quyết định, mở tab **Lịch sử**, sau đó quay lại dashboard để thấy quyết định gần nhất.
4. Cuộn xuống **Chứng minh hệ thống**: chỉ trạng thái “Không dùng API LLM ngoài”, checkpoint hash, metric và split đánh giá.
5. Mở `/readiness` nếu cần chứng minh adapter nào đang active trên máy demo.

Câu trả lời ngắn khi được hỏi “có phải chỉ gọi API ngoài không?”:

> Không. Request được xử lý trong tiến trình FastAPI local. Nhóm tự huấn luyện XGBoost, fine-tune YOLOv8s-seg và LayoutLMv3; DiT và PaddleOCR là checkpoint pretrained được tải về rồi suy luận local và được nhóm đánh giá riêng. Rules và NetworkX là thuật toán xác định. Mỗi artifact có version, SHA-256, metric và split đánh giá trong model registry. Màn hình model proof và `/readiness` cho thấy checkpoint nào đang thực sự active. Hệ thống không gọi LLM để tạo kết luận claim.

Khi được hỏi về ảnh AI:

> Nhóm không tuyên bố có universal AI-image detector. Bản hiện tại chứng minh provenance, dấu phần mềm chỉnh sửa, ảnh trùng/gần trùng và reuse giữa hồ sơ. Ảnh AI không có marker vẫn có thể lọt; vì vậy kết quả là inconclusive và chuyển sang chụp hướng dẫn hoặc người duyệt. Pixel detector chỉ được bật sau khi benchmark ảnh bảo hiểm đúng miền đạt ngưỡng đã khóa.
