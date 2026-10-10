# Báo cáo mức sẵn sàng cho Tiến độ lần 2

**Ngày rà soát:** 10/10/2026  
**Trọng tâm yêu cầu:** Data + Baseline + Evaluation v1

## Tình hình chung

Phần kỹ thuật cốt lõi cho báo cáo lần 2 đã có: audit dữ liệu tabular, data dictionary, leakage check, baseline rule, bốn model tabular, model selection, metrics và phân tích hạn chế. Nhánh CarDD đã tiến xa hơn kế hoạch cũ: YOLOv8n baseline và YOLOv8s candidate đều hoàn tất; YOLOv8s đã được chọn bằng validation. Final test CarDD còn đúng một bước và chưa có số liệu tại thời điểm lập báo cáo này.

## Checklist deliverable

| Deliverable | Trạng thái | Bằng chứng hiện có | Việc còn lại |
|---|---|---|---|
| AI Canvas v1 | Chưa thấy file trong repo | Luồng hệ thống và nguyên tắc nằm trong `PROJECT_STATUS_REPORT.md` | Nhóm gom thành canvas một trang |
| Project Charter | Chưa thấy file riêng | Mục tiêu, phạm vi và nguyên tắc đã có trong status report | Chốt owner, timeline, in/out scope |
| Product Vision & Target Users | Một phần | Reviewer, giám định viên, SIU và human-in-the-loop đã mô tả | Viết thành mục riêng, thêm nhu cầu từng user |
| Stakeholder Map | Chưa có bản chính thức | Danh sách người hỗ trợ trong status report | Vẽ influence/interest và trách nhiệm |
| KPI Tree | Một phần | AP, ROC-AUC, Recall@K, Precision@K, queue rate, calibration | Nối business KPI → operation KPI → model metric |
| Competitor/Product Comparison | Chưa có | Chưa có artifact trong repo | So sánh rule/manual review/build/API theo tiêu chí thống nhất |
| Data Source Plan | Đã có v1 | `DOCUMENT_DATA_SOURCE_PLAN_V1.md`, roadmap multimodal | Audit sáu thư mục dữ liệu thật |
| Risk Register | Có phần kỹ thuật v2 | `risk_register_v2_additions.md` | Ghép với Risk Register v1 của nhóm thành một bảng |
| Backlog + Sprint Plan | Chưa thấy file | Roadmap kỹ thuật có thứ tự ưu tiên | Chuyển thành backlog có PIC, deadline, definition of done |
| Mockup/user workflow | Có workflow chữ | Claim intake → signals → risk score → review | Làm mockup đơn giản nếu giảng viên cần hình |
| Data Audit Report | Hoàn thành v1 | `data_audit_report.md`, CarDD audit | Thêm audit document sau inventory |
| Data Dictionary/KB Audit | Tabular đã hoàn thành | `data_dictionary.md` | Document field dictionary chưa audit |
| EDA/source analysis | Hoàn thành cho tabular và CarDD | status report, leakage/robustness, CarDD reports | Chưa có EDA sáu nguồn document |
| Ground Truth Definition | Một phần | Fraud target và CarDD annotation đã mô tả | Viết protocol OCR/KIE; RAG citation policy chỉ khi dùng RAG |
| Data Leakage Check | Hoàn thành v1 | `reports/leakage/`, feature policy, split near-duplicate CarDD | Document split leakage chưa audit |
| Baseline process/model | Hoàn thành | Rule + XGBoost tabular; YOLOv8n/YOLOv8s CarDD | CarDD final test còn chờ |
| Model Selection Matrix | Hoàn thành tabular; CarDD đã khóa | `model_selection_matrix.md`, `CARDD_MODEL_SELECTION_V1.md` | Thêm document build/buy matrix sau audit |
| Metrics v1 | Hoàn thành tabular; CarDD validation xong | `metrics_v1.md`, CarDD validation reports | Thêm CarDD final-test metric sau khi chạy một lần |
| RAG prompt/retrieval test | Chưa áp dụng | Chưa chọn RAG làm baseline | Chỉ làm nếu scope chính thức có RAG |

## Kết quả nên trình bày

### Tabular fraud-risk baseline

- 1.000 hồ sơ, 247 fraud; Gold: 700 train, 100 validation, 200 test.
- XGBoost được chọn bằng repeated stratified CV.
- Frozen-test AP `0,559`, ROC-AUC `0,825`, Recall@10% `22,4%`, Precision@10% `55,0%`.
- Rule baseline Recall@10% `16,3%`; cải thiện `+6,1` điểm phần trăm, chưa đạt KPI đề xuất `+10` điểm.
- Test tabular đã dùng lại cho sensitivity check, vì vậy các quyết định feature tiếp theo dùng `train_fs`/`val_fs` và cần external test mới.

### CarDD damage segmentation

- 2.816 ảnh, 6.211 damage instance, sáu lớp.
- Split cố định: 1.966 train, 431 validation, 419 test; near-duplicate không bị tách chéo split.
- YOLOv8n validation mask mAP50-95 `0,5175`.
- YOLOv8s validation mask mAP50-95 `0,5284`, tăng `0,0109` và vừa đủ vượt ngưỡng chọn model `0,0100`.
- Checkpoint YOLOv8s đã khóa bằng SHA-256 `6c0d828760a427d48623653dcd6fffeb1cf591045d9ce8b8684a1d0f5f89420b`.
- Final test chưa chạy tại thời điểm báo cáo; không được điền số liệu test dự đoán.

## Cách kể câu chuyện khi trình bày trực tiếp

1. Bắt đầu bằng quyết định hỗ trợ reviewer, không tự kết luận gian lận.
2. Trình bày data lineage và split trước model metric.
3. Nêu baseline rule trước XGBoost để người nghe thấy mức cải thiện thực tế.
4. Với CarDD, giải thích đây là module nhận diện hư hại độc lập, chưa liên kết claim-level.
5. Trình bày cả lớp mạnh và lớp yếu; `crack`, `dent`, `scratch` vẫn là giới hạn.
6. Kết thúc bằng các rủi ro: nhãn, feature timing, bias/proxy, prevalence mismatch, license và thiếu linkage multimodal.

## Ưu tiên tiếp theo

1. Chạy CarDD final test bằng notebook one-shot và cập nhật metric thật.
2. Inventory sáu nguồn document đã có; kiểm tra license, schema, split và dung lượng.
3. Chọn một baseline document nhỏ, tránh tải/chạy toàn bộ RVL-CDIP khi chưa cần.
4. Hoàn thiện các tài liệu quản trị còn thiếu: Canvas, Charter, Stakeholder Map, KPI Tree, Backlog và Mockup.
5. Chỉ mở nhánh NetworkX khi có entity-edge và `event_time`; dữ liệu document công khai không tạo được graph fraud claim-level.

