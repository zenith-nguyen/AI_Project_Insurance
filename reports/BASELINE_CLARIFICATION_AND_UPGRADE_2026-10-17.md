# Baseline là gì và nhóm đã thực sự làm gì? — 2026-10-17

## Câu trả lời ngắn

Baseline không đồng nghĩa “model lấy từ một đường link bên ngoài”. Baseline là **mốc tối thiểu có thể tái lập** để biết một candidate phức tạp hơn có tạo thêm giá trị hay không.

Dự án tách rõ bốn lớp:

1. **Nguồn bên ngoài:** kiến trúc, pretrained checkpoint hoặc dataset công khai.
2. **Baseline của dự án:** mốc đơn giản được nhóm chạy lại trên split đã khóa.
3. **Candidate:** model/cấu hình phức tạp hơn, chỉ được chọn trên validation theo rule đặt trước.
4. **Final result:** đánh giá candidate đã khóa; final test không được dùng để sửa model.

Việc dùng YOLO, XGBoost, LayoutLMv3 hoặc PaddleOCR mã nguồn mở không làm mất phần đóng góp của nhóm. Phần phải nói chính xác là nhóm đã tự train/fine-tune model nào, chỉ benchmark model nào, và tự xây thuật toán nào.

## Bản đồ nguồn gốc và đóng góp

| Module | Nguồn bên ngoài | Baseline do nhóm chạy | Nhóm train/fine-tune? | Candidate/phiên bản hiện tại | Có uplift hợp lệ? |
|---|---|---|---|---|---|
| XGBoost | Thư viện XGBoost; dữ liệu nghiên cứu Kaggle | Rule baseline v1; Logistic Regression là simple-ML reference | Có, nhóm huấn luyện và hiệu chuẩn XGBoost | `tabular_v1` | AP 0,424 → 0,559 trên cùng frozen test; Recall@10% +6,1 điểm %, chưa đạt KPI +10 |
| YOLO | Kiến trúc/trọng số khởi tạo Ultralytics; CarDD | YOLOv8n-seg do nhóm fine-tune | Có, nhóm fine-tune cả baseline và candidate | YOLOv8s-seg candidate v1 | Validation mask mAP50-95 0,5175 → 0,5284, +0,0109; đúng ngưỡng chọn |
| DiT | Checkpoint Microsoft fine-tuned trên RVL-CDIP | Chính checkpoint pretrained | Không | Cùng DiT, nhóm tự chạy independent validation | Không có candidate riêng; macro-F1 0,9283 là benchmark của nhóm, không phải model nhóm train |
| PaddleOCR | Engine/checkpoint PaddleOCR | PaddleOCR pretrained trên SROIE | Không train từ đầu; nhóm chọn cấu hình runtime | `vi-robust` cho demo | Không công bố uplift 0,4097 → 0,1802 vì hai số thuộc hai dataset khác nhau |
| LayoutLMv3 | `microsoft/layoutlmv3-base` | Rule KIE v1 do nhóm viết | Có, nhóm fine-tune LayoutLMv3 | checkpoint-264 | Validation field F1 0,6834 → 0,9214, +0,2380; final test 0,8659 |
| Consistency | Python | Rule v2 do nhóm xây | Không phải model train | Rule v2 | Chỉ có engineering contract; chưa có precision nghiệp vụ |
| Quan hệ | NetworkX | Point-in-time graph v2 do nhóm xây | Không phải model train | Graph v2 | Chỉ có scenario tổng hợp; chưa có benchmark mạng lưới thật |
| Nguồn gốc ảnh | C2PA/tooling và thư viện ảnh | Pipeline provenance/reuse v4 do nhóm tích hợp | Pixel detector chưa được promote | Pipeline nhiều lớp | Chưa có accuracy phát hiện ảnh AI đúng miền |

## Vì sao không lấy metric từ bài báo/link ngoài làm baseline chính?

Metric công bố ở link ngoài thường khác split, preprocessing, phiên bản dependency và phần cứng. So sánh trực tiếp với metric đó có thể sai. Dự án dùng link ngoài để ghi **nguồn model/dataset**, còn baseline dùng để quyết định phải được nhóm chạy lại trong protocol của dự án.

Ngoại lệ là khi chưa có quyền hoặc tài nguyên chạy lại. Khi đó số bên ngoài chỉ được ghi là `external_reference`, không được ghi là kết quả baseline của nhóm.

## Cách đọc ba ví dụ quan trọng

### XGBoost

Rule baseline AP 0,424 và XGBoost AP 0,559 đều được đo trên frozen test 200 hồ sơ, nên có thể nói uplift AP là +0,135. Tuy nhiên Recall@10% chỉ tăng 6,1 điểm phần trăm, thấp hơn mục tiêu +10. Kết luận đúng là “candidate tốt hơn baseline nghiên cứu nhưng chưa đạt KPI”, không phải “model đã sẵn sàng chống gian lận”.

### YOLO

YOLOv8n và YOLOv8s đều khởi đầu từ công nghệ bên ngoài, nhưng nhóm tự fine-tune trên cùng CarDD split. Vì cùng validation 431 ảnh, chênh lệch +0,010865 là so sánh hợp lệ. Nhóm chọn YOLOv8s theo gate +0,0100 đã khóa; candidate vẫn yếu ở crack/dent/scratch và chậm hơn.

### LayoutLMv3

Rule KIE do nhóm viết đạt validation field F1 0,6834. LayoutLMv3 dùng base checkpoint Microsoft nhưng nhóm fine-tune đạt 0,9214 trên cùng validation, tăng khoảng 23,8 điểm F1. Sau khi khóa checkpoint, final test đạt 0,8659. Đây là ví dụ rõ nhất về “dùng nền tảng bên ngoài nhưng phần fine-tune, protocol và đánh giá là công việc của nhóm”.

## Baseline upgrade đã triển khai

- `configs/baseline_registry.v1.yaml` là nguồn sự thật cho ownership, metric, split, uplift và giới hạn.
- `GET /system/baselines` cung cấp dữ liệu cho UI và đội kỹ thuật.
- Dashboard hiển thị baseline → current, loại nguồn, phần nhóm đã làm, khả năng so sánh và kết luận nghiệp vụ.
- `scripts/check_baseline_registry.py` chặn việc công bố delta nếu khác split hoặc phép tính không khớp.
- Test contract bảo đảm đủ baseline cho toàn bộ module trong model registry.

## Mốc nâng cấp tiếp theo

1. Tabular: phát triển S1–S5 trên `train_fs/val_fs`; sau khi khóa mới dùng external test mới.
2. YOLO: thêm ảnh Việt Nam có mask và KPI `useful-region rate`, không chỉ mAP.
3. OCR: chạy baseline và candidate trên cùng 50–100 trang thật, đo CER, field accuracy, latency và correction time.
4. DiT/LayoutLMv3: taxonomy và validation cho biên bản, báo giá, hóa đơn và đăng ký xe Việt Nam.
5. Graph/rules/authenticity: tạo ground truth nghiệp vụ để thay `engineering_demo` bằng precision/recall và false-positive cost.

## Câu trình bày trước lớp

> Nhóm có sử dụng kiến trúc và pretrained checkpoint mã nguồn mở, nhưng không lấy metric trên Internet rồi nhận là kết quả của dự án. Baseline là mốc nhóm tái lập trên split đã khóa. Nhóm tự huấn luyện XGBoost, fine-tune YOLOv8s-seg và LayoutLMv3; DiT và PaddleOCR là model pretrained được nhóm benchmark độc lập; rules, NetworkX và pipeline xác minh ảnh do nhóm triển khai. Dashboard công khai nguồn gốc, checkpoint, split, metric, mức tăng so với baseline và giới hạn của từng module.
