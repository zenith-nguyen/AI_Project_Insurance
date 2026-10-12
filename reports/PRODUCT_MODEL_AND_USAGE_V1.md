# Model và sản phẩm cuối — v1

## Sản phẩm là gì

Sản phẩm đề xuất là **hệ thống hỗ trợ duyệt hồ sơ bồi thường bảo hiểm xe cơ giới**. Hệ thống nhận dữ liệu hồ sơ, ảnh xe và chứng từ; tạo các tín hiệu có bằng chứng để reviewer/giám định viên/SIU ưu tiên kiểm tra. Hệ thống không tự kết luận gian lận và không tự từ chối bồi thường.

Tên mô tả dùng trong báo cáo: **AI-assisted Motor Insurance Claim Review System**.

## Không phải một model duy nhất

| Module | Model/trạng thái | Output |
|---|---|---|
| Tabular risk ranking | XGBoost baseline nghiên cứu đã chạy | Risk score và explanation cho hồ sơ bảng |
| Damage understanding | YOLOv8s-seg đã khóa/final-test | Mask, loại hư hại, confidence |
| Document classification | DiT baseline đã smoke-test; independent validation chờ chạy | Loại chứng từ |
| OCR | PaddleOCR baseline đã đo trên SROIE validation | Text và vị trí |
| Key Information Extraction | Rule baseline; LayoutLMv3 candidate đã chọn trên validation | Hiện mới hỗ trợ trường ngày và tổng tiền |
| Consistency checks | Rules/versioned code; synthetic demo PASS | Cờ sai lệch giữa form, hóa đơn và claim |
| Relationship risk | NetworkX point-in-time demo PASS; GNN chỉ khi đủ dữ liệu | Đặc trưng quan hệ và cảnh báo pattern |

Hiện nhánh tabular, CarDD và document đều đã có metric module-level. Document gồm DiT smoke macro-F1 0,9626, PaddleOCR CER 0,4097/WER 0,5592, rule KIE F1 0,6834 và LayoutLMv3 validation F1 0,9214. LayoutLMv3 mới được chọn trên validation và test vẫn khóa; NetworkX mới chứng minh logic bằng synthetic demo vì public datasets không có quan hệ claim-level thật.

## Luồng sử dụng sau này

1. Nhân viên tạo hoặc nhập `claim_id`.
2. Người dùng tải ảnh xe và các chứng từ của cùng claim.
3. YOLOv8s-seg khoanh vùng hư hỏng trên ảnh xe.
4. Document pipeline xác định loại tài liệu, OCR và trích xuất trường.
5. Rules kiểm tra số tiền, ngày, biển số, số hợp đồng và các trường giữa tài liệu.
6. Khi có dữ liệu nghiệp vụ hợp lệ, tabular/graph module tạo risk signals.
7. API hợp nhất output theo `claim_id` và trả evidence, confidence, model version, trace ID.
8. UI hiển thị ảnh có mask, trường trích xuất, cờ bất nhất và lý do xếp hạng cho reviewer.
9. Reviewer sửa kết quả hoặc quyết định bước xử lý; mọi sửa đổi được audit-log làm feedback có kiểm soát.

## Ví dụ output API mục tiêu

```json
{
  "claim_id": "CLM-2026-000123",
  "damage": {
    "model": "cardd-yolov8s-seg-v1",
    "findings": [
      {"class": "dent", "confidence": 0.81, "mask_uri": "..."}
    ]
  },
  "documents": {
    "status": "candidate_selected_on_validation_final_test_locked",
    "fields": []
  },
  "risk": {
    "score": null,
    "reason": "claim-level production model is not yet validated"
  },
  "decision": "manual_review",
  "human_review_required": true,
  "trace_id": "..."
}
```

## Cách dùng checkpoint CarDD hiện tại

Checkpoint trên Drive:

```text
/content/drive/MyDrive/AI_Project_Insurance_Acc 2/artifacts/image/cardd_yolov8s_seg_candidate_v1/weights/best.pt
```

Inference thử nghiệm bằng Python:

```python
from ultralytics import YOLO

model = YOLO("/path/to/best.pt")
results = model.predict(source="damage_photo.jpg", imgsz=640, conf=0.25)
for result in results:
    result.save(filename="damage_prediction.jpg")
```

Trong sản phẩm, đoạn inference phải được đặt trong module/service có schema input-output cố định, không gọi trực tiếp từ notebook. API cần trả model version, checkpoint SHA-256, confidence và trace ID.

## Lộ trình thành MVP

1. Đóng SROIE processed data gate.
2. Chạy baseline classification/OCR/KIE và chọn model bằng validation.
3. Viết inference package cho CarDD và document pipeline.
4. Tạo FastAPI contract nhận `claim_id`, ảnh và chứng từ.
5. Tạo UI reviewer: upload, preview mask, sửa field, xem cảnh báo.
6. Chạy golden-set integration test, security test và UAT nội bộ.
7. Pilot có human review; chưa tự động từ chối claim.
8. Chỉ go-live sau khi có dữ liệu bảo hiểm thật, PII/license approval, monitoring và rollback.

## Câu trả lời ngắn khi giảng viên hỏi

“Nhóm xây một hệ thống hỗ trợ reviewer, không phải một model gian lận duy nhất. Hiện XGBoost tạo baseline risk từ dữ liệu bảng và YOLOv8s-seg nhận diện hư hại. Nhánh chứng từ đang được chuẩn bị để phân loại, OCR và trích xuất trường. Các module chỉ hợp nhất bằng claim_id thật; output là risk signals và evidence cho con người quyết định.”
