# Kế hoạch đưa phân tích hư hỏng ảnh vào sản phẩm — v1

**Ngày:** 13/10/2026
**Model đã khóa:** YOLOv8s-seg `cardd_candidate_v1`
**Checkpoint SHA-256:** `6c0d828760a427d48623653dcd6fffeb1cf591045d9ce8b8684a1d0f5f89420b`

## Mục tiêu sản phẩm

Khi người dùng nộp ảnh xe, hệ thống phải tự động:

1. lưu file, hash và kiểm tra khả năng tái sử dụng ảnh;
2. chạy YOLO bằng checkpoint đúng hash;
3. khoanh vùng hư hỏng và trả nhãn, confidence, bounding box/mask;
4. hiển thị lớp phủ trên ảnh trong workbench;
5. so sánh hư hỏng với lời khai và chứng từ;
6. ghi rõ trạng thái `completed`, `unavailable` hoặc `failed`, không biến thiếu model thành điểm rủi ro bằng 0.

Kết quả là tín hiệu hỗ trợ nhân viên. Nó không tự xác định gian lận, nguyên nhân tai nạn hay chi phí sửa chữa.

## Trạng thái đầu vào

- Training/model selection/final test CarDD đã hoàn tất.
- Final-test mask mAP50-95: `0,513978` trên 419 ảnh.
- Lớp tốt: `glass shatter` 0,9179; `tire flat` 0,8513; `lamp broken` 0,6702.
- Lớp yếu: `crack` 0,0863; `dent` 0,2779; `scratch` 0,2804.
- API adapter và kiểm tra checkpoint hash đã có.
- Máy tích hợp local hiện thiếu `best.pt`, nên `/readiness` báo `damage_segmentation.active = false`.

## Mốc triển khai

### Mốc D1 — Gắn artifact đã khóa

1. Tải `best.pt` từ Drive dùng chung về artifact root.
2. Chạy `scripts/setup_live.ps1 -ArtifactRoot <artifact-root> -InstallMultimodalDependencies`.
3. Xác nhận file nằm tại `artifacts/models/damage_segmentation/cardd_candidate_v1/best.pt`.
4. Bắt buộc hash khớp registry; sai hash thì dừng.
5. Khởi động lại API bằng `scripts/run_live.ps1` và kiểm tra `/readiness`.

**Gate D1:** `damage_segmentation.active = true`, đúng SHA-256 và không đọc lại final test.

### Mốc D2 — Smoke test trên ảnh ngoài tập CarDD

Chạy:

```powershell
.venv\Scripts\python.exe scripts\run_damage_inference.py `
  "D:\My Dowload\case_02_vehicle.png" `
  --output-dir "D:\My Dowload\CASE_02_DAMAGE_OUTPUT"
```

Đầu ra gồm JSON detection và ảnh overlay. Sau đó nạp cùng ảnh vào `/intake` để xác nhận API trả `module_status.damage_segmentation.status = completed`.

**Gate D2:** một ảnh mới sinh được JSON + overlay; UI hiển thị nhãn, confidence và liên kết về evidence ID.

### Mốc D3 — Error analysis đúng miền Việt Nam

Tạo benchmark mới, tách theo `incident_id`/`vehicle_id`, gồm tối thiểu:

- ảnh toàn cảnh và cận cảnh;
- ngày/đêm, mưa, phản sáng;
- ảnh nén qua Zalo/Facebook;
- nhiều mức độ hư hỏng và ảnh không hư hỏng;
- xe máy/xe tải xuất hiện cạnh xe claim;
- ảnh có cản rời, nắp capo biến dạng và hư hỏng kết cấu.

Đánh giá per-class precision/recall/AP, false negative ở hư hỏng nặng, false positive trên bóng/đất bẩn và latency CPU/GPU. Không dùng final test CarDD để chỉnh threshold.

**Gate D3:** có dataset card, split chống leakage, error gallery và ngưỡng validation theo từng lớp.

### Mốc D4 — Mở rộng taxonomy

CarDD v1 chỉ có `crack`, `dent`, `glass shatter`, `lamp broken`, `scratch`, `tire flat`. Case va chạm mạnh còn cần tối thiểu:

- `bumper_detached_or_broken`;
- `hood_deformation`;
- `structural_front_damage`;
- `panel_missing`;
- `unknown_severe_damage` để chuyển người duyệt khi ngoài taxonomy.

Chỉ fine-tune candidate mới trên train/validation mới. Giữ nguyên kết quả model v1; version candidate thành v2 và đánh giá trên test miền Việt Nam được khóa riêng.

**Gate D4:** recall hư hỏng nặng đạt ngưỡng nghiệp vụ đã thống nhất và không giảm quá mức ở các lớp v1.

### Mốc D5 — Đối chiếu ảnh với claim và chứng từ

- Biển số/loại xe/màu xe phải được liên kết với claim.
- Vị trí hư hỏng phải so sánh với mô tả tai nạn và biên bản.
- Số tiền chỉ được kiểm tra khi có báo giá/hóa đơn; biên bản hiện trường không phải chứng từ chi phí.
- Mâu thuẫn tạo signal có evidence ID; thiếu dữ liệu tạo trạng thái `unknown`, không tạo kết luận gian lận.

**Gate D5:** golden claim chạy xuyên suốt ảnh → damage → document fields → consistency → workbench → review log.

## Definition of Done cho nhánh ảnh hư hỏng

Nhánh này chỉ được xem là hoàn thành khi:

1. checkpoint đúng hash được đóng gói và người khác setup được bằng một lệnh;
2. `/readiness` báo active và smoke test chạy qua;
3. UI hiển thị mask/box cùng model version và confidence;
4. có benchmark Việt Nam chống leakage và báo cáo theo lớp;
5. taxonomy xử lý được hư hỏng nặng hoặc trả `unknown` rõ ràng;
6. ảnh thiếu/mờ/ngoài miền không làm API lỗi và không bị hiểu thành “không hư hỏng”;
7. kết quả được lưu trong audit trail, có thể sửa bởi người duyệt;
8. đạt latency, security/privacy và UAT đã khóa cho pilot.

## Ưu tiên ngay

1. Copy checkpoint và bật inference local (D1).
2. Chạy case người dùng vừa gửi, lưu overlay/JSON (D2).
3. Tạo bộ 20–50 ảnh Việt Nam đầu tiên cho error analysis; chưa cần train lại ngay.
4. Thiết kế UI overlay và trường xác nhận/sửa nhãn.
5. Sau khi thấy lỗi thật mới quyết định mở rộng dữ liệu và train candidate v2.
