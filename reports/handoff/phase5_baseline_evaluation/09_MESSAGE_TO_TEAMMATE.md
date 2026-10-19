# Tin nhắn gửi thành viên phụ trách

Bạn phụ trách **Phase 5 — Baseline B0–B5 & Evaluation Report**. Mình đã chuẩn bị task brief, protocol chống leakage, data contract, runbook, report template, checklist và evaluator trong gói này.

Việc đầu tiên là đọc `00_README.md` rồi xác nhận định nghĩa B0–B5 trong `configs/phase5_evaluation.v1.yaml`. Trước mắt chạy B0 Rule, B1 Logistic Regression và B2 XGBoost trên cùng `train_fs/val_fs`. B3–B5 chỉ được đánh giá khi document/image/graph thật sự thuộc cùng `claim_id` và có timestamp trước lúc chấm; không ghép Kaggle, CarDD và SROIE thành claim giả.

Output cần có AP, Recall/Precision@5/10/20%, PR curve, paired bootstrap 1.000 lần và CI hiệu số. Nếu CI chứa 0, kết luận là “chưa đủ bằng chứng candidate tốt hơn”. Frozen test cũ không được dùng để chọn feature/cấu hình mới. Khi có prediction CSV đúng schema, chạy lệnh trong `04_RUNBOOK.md`.
