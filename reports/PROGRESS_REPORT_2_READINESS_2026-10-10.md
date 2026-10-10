# Báo cáo mức sẵn sàng cho Tiến độ lần 2

**Ngày rà soát:** 10/10/2026  
**Trọng tâm yêu cầu:** Data + Baseline + Evaluation v1

## Tình hình chung

Phần kỹ thuật cốt lõi cho báo cáo lần 2 đã có: audit dữ liệu tabular, data dictionary, leakage check, baseline rule, bốn model tabular, model selection, metrics và phân tích hạn chế. Nhánh CarDD đã hoàn tất training, model selection và final test đúng một lần. YOLOv8s được chọn bằng validation; final-test artifact verification PASS với mask mAP50-95 `0,513978`. Không chạy final test lần hai.

## Checklist deliverable

| Deliverable | Trạng thái | Bằng chứng hiện có | Việc còn lại |
|---|---|---|---|
| AI Canvas v1 | Nhóm xác nhận đã có ngoài repo kỹ thuật | Artifact business do nhóm quản lý | Không làm lại trong nhánh kỹ thuật |
| Project Charter | Nhóm xác nhận đã có ngoài repo kỹ thuật | Artifact business do nhóm quản lý | Không làm lại trong nhánh kỹ thuật |
| Product Vision & Target Users | Một phần | Reviewer, giám định viên, SIU và human-in-the-loop đã mô tả | Viết thành mục riêng, thêm nhu cầu từng user |
| Stakeholder Map | Nhóm xác nhận đã có ngoài repo kỹ thuật | Artifact business do nhóm quản lý | Không làm lại trong nhánh kỹ thuật |
| KPI Tree | Một phần | AP, ROC-AUC, Recall@K, Precision@K, queue rate, calibration | Nối business KPI → operation KPI → model metric |
| Competitor/Product Comparison | Nhóm xác nhận đã có ngoài repo kỹ thuật | Artifact business do nhóm quản lý | Không làm lại trong nhánh kỹ thuật |
| Data Source Plan | Đã có v1 và audit link | `DOCUMENT_DATA_SOURCE_PLAN_V1.md`, `DOCUMENT_SOURCE_LINK_AUDIT_V1.md` | Audit sáu thư mục dữ liệu thật |
| Risk Register | Có phần kỹ thuật v2 | `risk_register_v2_additions.md` | Ghép với Risk Register v1 của nhóm thành một bảng |
| Backlog + Sprint Plan | Nhóm xác nhận đã có ngoài repo kỹ thuật | Artifact business do nhóm quản lý | Không làm lại trong nhánh kỹ thuật |
| Mockup/user workflow | Nhóm xác nhận đã có ngoài repo kỹ thuật | Artifact business do nhóm quản lý | Không làm lại trong nhánh kỹ thuật |
| Data Audit Report | Hoàn thành v1 | `data_audit_report.md`, CarDD audit | Thêm audit document sau inventory |
| Data Dictionary/KB Audit | Tabular đã hoàn thành; document integration schema v1 đã có | `data_dictionary.md`, `DOCUMENT_CLAIM_INTEGRATION_CONTRACT_V1.md` | Audit field dictionary trên dữ liệu document thật |
| EDA/source analysis | Hoàn thành cho tabular và CarDD | status report, leakage/robustness, CarDD reports | Chưa có EDA sáu nguồn document |
| Ground Truth Definition | Một phần | Fraud target và CarDD annotation đã mô tả | Viết protocol OCR/KIE; RAG citation policy chỉ khi dùng RAG |
| Data Leakage Check | Hoàn thành v1 | `reports/leakage/`, feature policy, split near-duplicate CarDD | Document split leakage chưa audit |
| Baseline process/model | Hoàn thành | Rule + XGBoost tabular; YOLOv8n/YOLOv8s CarDD; final test đã khóa | Không chạy lại CarDD test |
| Model Selection Matrix | Hoàn thành tabular; CarDD đã khóa | `model_selection_matrix.md`, `CARDD_MODEL_SELECTION_V1.md` | Thêm document build/buy matrix sau audit |
| Metrics v1 | Hoàn thành tabular và CarDD | `metrics_v1.md`, `CARDD_FINAL_TEST_V1.md`, CarDD JSON reports trên Drive | Bổ sung error gallery/model card nếu cần trình bày |
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
- Final test 419 ảnh/931 instance: mask mAP50-95 `0,513978`, mask mAP50 `0,681571`, box mAP50-95 `0,539952`.
- Artifact verification PASS; không chạy lại test hoặc tinh chỉnh theo test.

## Cách kể câu chuyện khi trình bày trực tiếp

1. Bắt đầu bằng quyết định hỗ trợ reviewer, không tự kết luận gian lận.
2. Trình bày data lineage và split trước model metric.
3. Nêu baseline rule trước XGBoost để người nghe thấy mức cải thiện thực tế.
4. Với CarDD, giải thích đây là module nhận diện hư hại độc lập, chưa liên kết claim-level.
5. Trình bày cả lớp mạnh và lớp yếu; `crack`, `dent`, `scratch` vẫn là giới hạn.
6. Kết thúc bằng các rủi ro: nhãn, feature timing, bias/proxy, prevalence mismatch, license và thiếu linkage multimodal.

## Ưu tiên tiếp theo

1. Inventory sáu nguồn document đã có; kiểm tra license, schema, split và dung lượng.
2. Chọn một baseline document nhỏ, tránh tải/chạy toàn bộ RVL-CDIP khi chưa cần.
3. Hoàn thiện model card/error gallery CarDD nếu cần cho buổi trình bày; không mở lại model selection.
4. Không làm lại các artifact business mà nhóm đã xác nhận đang có; chỉ tham chiếu chúng khi trình bày.
5. Chỉ mở nhánh NetworkX khi có entity-edge và `event_time`; dữ liệu document công khai không tạo được graph fraud claim-level.

