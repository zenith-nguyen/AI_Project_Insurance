# 06 — Review checklist và Definition of Done

## Data

- [ ] Cùng `claim_id` giữa label, tabular, document, image và graph.
- [ ] Không có cross-split duplicate/leakage.
- [ ] Mọi feature có `available_at/received_at <= scored_at`.
- [ ] Train/validation/test hash được lưu.
- [ ] PII không vào GitHub public.

## Experiment

- [ ] B0–B5 được khóa trước final test.
- [ ] B0/B1/B2 dùng cùng feature eligibility và split.
- [ ] Preprocessing fit trong fold/train.
- [ ] Threshold/calibration không fit bằng test.
- [ ] Seed/config/dependency/model hash được ghi.

## Evaluation

- [ ] AP, Recall@5/10/20%, Precision@5/10/20%.
- [ ] Bootstrap phân tầng 1.000 lần.
- [ ] Paired delta CI cho comparison đã khóa.
- [ ] PR curve và Recall/Precision@K curve.
- [ ] CI chứa 0 được kết luận “chưa đủ bằng chứng”.
- [ ] Error analysis top queue.

## Business

- [ ] Nói rõ score dùng xếp hàng, không kết luận fraud.
- [ ] K gắn với năng lực review.
- [ ] Có latency và fallback khi module thiếu.
- [ ] Có false hold/false investigation discussion.
- [ ] B3–B5 blocked nếu chưa có claim-linked labeled data.

## Definition of Done

Task chỉ DONE khi code chạy lại được, evidence có hash, report khớp JSON, reviewer kiểm tra leakage/comparison và mọi limitation được ghi. Nếu chưa có external claim-linked test, trạng thái tối đa là **development evaluation complete**, không phải final/production validated.
