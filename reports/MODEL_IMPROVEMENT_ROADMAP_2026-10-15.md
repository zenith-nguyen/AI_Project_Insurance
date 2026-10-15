# Kế hoạch nâng cấp model và giá trị nghiệp vụ

Ngày cập nhật: 2026-10-15.

Kế hoạch thực thi theo mốc, KPI và Definition of Done: [NEXT_UPGRADE_EXECUTION_PLAN_2026-10-15.md](NEXT_UPGRADE_EXECUTION_PLAN_2026-10-15.md).

Kết quả candidate OCR/KIE và benchmark ba hồ sơ: [OCR_KIE_CANDIDATE_BENCHMARK_2026-10-15.md](OCR_KIE_CANDIDATE_BENCHMARK_2026-10-15.md).

Kết quả preload và cache theo từng evidence: [INCREMENTAL_CACHE_AND_PRELOAD_VALIDATION_2026-10-16.md](INCREMENTAL_CACHE_AND_PRELOAD_VALIDATION_2026-10-16.md).

## Nguyên tắc

Mỗi nâng cấp phải đồng thời trả lời hai câu hỏi:

1. **Technical value:** metric nào tốt hơn trên tập validation chưa dùng để tối ưu?
2. **Business value:** thay đổi đó giúp người duyệt tìm đúng hồ sơ, đọc nhanh hơn hay giảm yêu cầu bổ sung như thế nào?

Không điều chỉnh model bằng final test đã khóa. Không bật một module trong quyết định nghiệp vụ chỉ vì demo nhìn hợp lý; module phải có dữ liệu đúng miền, threshold khóa, báo cáo lỗi và cơ chế fallback cho con người.

## Thứ tự ưu tiên

### P0 — Golden claims và đo end-to-end

Tạo 20–50 claim tổng hợp/ẩn danh có chung `claim_id`, gồm dữ liệu bảng, nhiều góc ảnh, chứng từ, entity graph và expected action. Đo:

- tỷ lệ claim chạy đủ các module;
- thời gian từ upload đến kết quả;
- tỷ lệ field phải sửa;
- số cảnh báo đúng/sai;
- khả năng lưu và đọc lại review/audit.

Điều kiện đạt: không mất liên kết claim, không im lặng khi module lỗi, mọi kết quả đều chỉ được evidence và version model.

### P1 — PaddleOCR và chứng từ Việt Nam

Hiện CER 40,97% là điểm yếu rõ nhất. Thực hiện error analysis theo ảnh xoay, mờ, chữ nhỏ, dấu tiếng Việt, bảng và con dấu; sau đó thử orientation/deskew, crop, contrast và cấu hình OCR tiếng Việt trên validation riêng.

Business KPI: giảm số trường người duyệt phải nhập lại và giảm thời gian đọc một chứng từ. Gate đề xuất trước pilot: field accuracy cho các trường nghiệp vụ trọng yếu và correction rate được đo trên chứng từ bảo hiểm Việt Nam.

### P1 — XGBoost xếp hạng claim

Phát triển feature S1–S5 trên `train_fs/val_fs`, ưu tiên feature có sẵn đúng thời điểm chấm. So sánh với Logistic Regression và rule baseline bằng AP, Recall@10%, precision trong queue, calibration và Net Value.

Business KPI: trong cùng năng lực duyệt 10%, tìm thêm claim cần điều tra mà không tăng quá nhiều false hold. Không đặt mục tiêu Recall@10% 60% trên dataset prevalence 24,7% vì trần toán học xấp xỉ 40,5%; cần đổi capacity K, dữ liệu hoặc định nghĩa KPI.

### P1 — YOLO hư hỏng đúng miền

Lập error gallery theo `crack`, `dent`, `scratch`, góc chụp, ánh sáng và loại xe. Bổ sung nhãn ảnh bảo hiểm gần với quy trình Việt Nam, kiểm tra annotation quality rồi fine-tune candidate mới trên train/validation.

Business KPI: tỷ lệ ảnh mà vùng khoanh giúp giám định viên xác định đúng vị trí cần kiểm tra; đo thêm false region/image và thời gian xem ảnh, không chỉ mAP.

### P2 — LayoutLMv3 và DiT

Giữ nguyên kết quả final test hiện tại. Tạo validation mới cho biên bản, báo giá, hóa đơn và giấy tờ tiếng Việt. Mở rộng schema KIE sau khi chốt field nghiệp vụ. DiT cần taxonomy và confusion matrix đúng bộ chứng từ nội bộ.

Business KPI: routing đúng loại chứng từ và extraction accuracy cho ngày, tổng tiền, biển số, đơn vị sửa chữa; mọi trường confidence thấp chuyển người duyệt.

### P2 — Consistency và NetworkX

Version hóa rule, threshold và tolerance; bổ sung entity normalization cho biển số, điện thoại và xưởng. Mọi edge phải có `available_at` để tránh dùng thông tin tương lai.

Business KPI: precision của cảnh báo mismatch/shared entity và số case điều tra hữu ích được mở rộng từ graph. Không có graph phải hiển thị “chưa có dữ liệu”, không phải “không có quan hệ”.

### P2 — Media authenticity

Tạo benchmark đúng miền với các nhóm:

- camera original;
- chỉnh sáng/crop hợp lệ;
- Photoshop/AI edit;
- Facebook/TikTok/re-encode;
- screenshot/re-capture;
- ảnh AI từ nhiều generator;
- ảnh exact và near-duplicate giữa claim.

Đo precision/recall theo từng nhóm, calibration, false accusation rate và coverage. Chỉ bật pixel forensic model khi manifest xác nhận đúng dataset version, threshold, calibration metric và hash checkpoint. UI luôn phân biệt `detected`, `not found`, `unavailable` và `inconclusive`.

Business KPI: phát hiện bằng chứng tái sử dụng hoặc thiếu provenance để yêu cầu ảnh tốt hơn, đồng thời giữ false accusation thấp. Module không tự kết luận gian lận.

## Roadmap phát hành

| Mốc | Sản phẩm bàn giao | Gate |
|---|---|---|
| R1 | One-link app, dashboard, workbench, audit, model proof | Test suite PASS; model/readiness hiển thị đúng |
| R2 | Golden claims end-to-end | Tất cả claim chạy lại được; expected action có sign-off |
| R3 | OCR/XGBoost/YOLO candidate mới | Validation cải thiện và business KPI không giảm |
| R4 | Domain validation Việt Nam | Dataset/label provenance, subgroup/error report hoàn chỉnh |
| R5 | Pilot nội bộ | Auth/RBAC, database, encryption, load/security test, UAT và rollback PASS |

## Definition of Done cho một model adapter

Một adapter chỉ được coi là hoàn thành khi có đủ artifact hash, schema input/output, metric và split, error analysis, latency, trạng thái khi thiếu input, fallback cho người dùng, audit trail và tài liệu giới hạn. “Model chạy được một ảnh” chưa phải Definition of Done.
