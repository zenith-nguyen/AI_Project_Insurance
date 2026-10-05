# Risk Register v2 — Các rủi ro mới

- **Bias từ `insured_hobbies` — Cao.** SHAP bị chi phối bởi `cross-fit`/`chess`, nhưng không có cơ sở nghiệp vụ. Mitigation: bật `EXCLUDE_BIASED_FEATURES`, báo cả sensitivity result và không trình bày hobbies như fraud indicator.
- **Prevalence mismatch — Cao.** Kaggle có 24,7% fraud, trong khi business giả định 5–10%. Precision/calibration/queue rate không chuyển trực tiếp sang production. Mitigation: external data hoặc scenario có giả định rõ ràng.
- **Provenance nhãn chưa xác minh — Cao.** Chưa biết `fraud_reported` là kết quả điều tra hay chỉ là fraud được báo cáo/phát hiện. Mitigation: truy nguồn dataset, ghi label definition và xem non-fraud là nhãn có thể nhiễu.
- **Feature timing chưa chốt — Cao.** Claim amounts, severity, police report và witnesses có thể chỉ xuất hiện sau intake. Mitigation: data dictionary theo checkpoint và hai feature policy riêng.
- **Test reuse — Trung bình.** Frozen test đã được dùng để so sánh policy loại bias. Mitigation: cần external test trước khi chốt feature/model cuối cùng.
- **License dữ liệu ngoài chưa xác minh — Cao.** CarDD, CORD, SROIE, FUNSD, XFUND, MIDV và RVL-CDIP chưa có license record đã đọc trong repo. Mitigation: đọc nguồn gốc/license sau khi tải, lưu manifest và không redistribute raw data trước khi duyệt.
- **Multimodal không liên kết — Cao.** CarDD, Kaggle và CORD không có `claim_id` chung. Mitigation: đánh giá từng module độc lập; chỉ fusion bằng dataset claim-level hợp lệ hoặc Layer C được mô tả rõ là synthetic.
- **Dataset nhỏ — Trung bình.** Chỉ có 247 fraud, frozen test có 49 fraud nên CI rộng. Mitigation: repeated CV, bootstrap CI và thu thập external validation.
