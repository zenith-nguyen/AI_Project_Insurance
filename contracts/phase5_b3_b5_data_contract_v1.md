# Phase 5 — B3-B5 Data & Point-in-Time Contract v1

**Mục đích:** định rõ dữ liệu cần có để chạy B3 (document), B4 (image) và B5 (consistency/relationship), sao cho khi có dữ liệu nối thật là chạy được ngay, không phải sửa format. Bổ sung cho `03_DATA_AND_PREDICTION_CONTRACT.md` và `configs/phase5_evaluation.v1.yaml`.

> Nguyên tắc tối cao: **KHÔNG ghép** một dòng Kaggle, một ảnh CarDD và một hóa đơn SROIE rời nhau thành một "claim" giả để công bố metric B3-B5. Mọi bằng chứng phải thuộc **cùng một `claim_id` thật**.

## 1. Khóa liên kết và thời điểm

| Trường | Kiểu | Bắt buộc | Ý nghĩa |
|---|---|---|---|
| `claim_id` | string | ✓ | Khóa nối mọi nguồn với nhãn. Duy nhất ở bảng claim. |
| `fraud_label` | 0/1 | ✓ | Nhãn `fraud_reported` của chính claim đó. |
| `scored_at` | ISO 8601 | ✓ | Thời điểm chấm điểm (mốc quyết định). Một giá trị cho mỗi claim. |

**Quy tắc point-in-time (chống rò rỉ tương lai):** một mẩu bằng chứng chỉ được dùng để chấm một claim nếu thời điểm của nó **≤ `scored_at`** của claim đó.
- Document / image: `received_at ≤ scored_at`.
- Entity/relationship edge: `available_at ≤ scored_at`.
Bằng chứng có thời điểm sau `scored_at` phải **bị loại** khỏi lần chấm, không được đưa vào feature.

## 2. Bảng bằng chứng (evidence manifest)

Một bảng (CSV/Parquet) liệt kê mọi mẩu bằng chứng, mỗi dòng một mẩu:

| Cột | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `claim_id` | string | ✓ | Phải tồn tại ở bảng claim/predictions. |
| `modality` | enum | ✓ | `document` \| `image` \| `entity_edge`. |
| `evidence_id` | string | ✓ | Định danh mẩu bằng chứng. |
| `event_time` | ISO 8601 | ✓ | `received_at` (document/image) hoặc `available_at` (entity_edge). |
| `scored_at` | ISO 8601 | ✓ | Bằng `scored_at` của claim; giống nhau cho mọi dòng cùng claim. |
| `source` | string | ✓ | Nguồn gốc (đường dẫn hồ sơ thật, không phải dataset công khai rời). |

Ánh xạ stage → modality bắt buộc:
- **B3** cần ≥ 1 `document` cho mỗi claim được chấm.
- **B4** cần B3 + ≥ 1 `image`.
- **B5** cần B4 + ≥ 1 `entity_edge` point-in-time.

## 3. Bảng điểm (prediction file) nạp vào evaluator

Giống `phase5_predictions_SCHEMA_EXAMPLE.csv`: `claim_id, fraud_label, B0_score … B5_score`.
- Mọi stage được đánh giá phải chấm **đúng cùng tập claim theo cùng thứ tự**.
- Cột của stage bị chặn để trống (NaN), evaluator tự bỏ qua. **Không** điền 0 thay cho module thiếu.
- B3 = B2 + tín hiệu document; B4 = B3 + ảnh; B5 = B4 + consistency/relationship. Mỗi bậc chỉ thêm tín hiệu point-in-time hợp lệ.

## 4. Cổng hợp lệ (validator kiểm)

Một run B3-B5 chỉ hợp lệ khi:
1. `claim_id` duy nhất, không rỗng; `fraud_label` đủ hai lớp 0/1.
2. Cột điểm của stage được chấm phải **đầy đủ** (không NaN lác đác), hữu hạn.
3. Mọi `evidence.claim_id` tồn tại trong tập claim (referential integrity).
4. Mọi bằng chứng dùng để chấm có `event_time ≤ scored_at`.
5. Stage nào thiếu modality bắt buộc cho dù chỉ một claim → **đánh dấu blocked**, không được báo cáo metric.
6. Preprocessing/feature fit trong train/fold; feature không chứa target hoặc proxy sau quyết định.

Chạy kiểm: `python scripts/validate_b3_b5_contract.py <predictions.csv> [--evidence <manifest.csv>]`.
Kết quả: mỗi stage là `evaluable`, `blocked` (thiếu bằng chứng) hoặc `leakage` (bằng chứng sau `scored_at`), kèm verdict `PASS` / `BLOCKED` / `FAIL`.

## 5. Sau khi có dữ liệu

Khi bảng bằng chứng thật sẵn sàng: (a) chạy validator để chắc point-in-time và liên kết đúng; (b) sinh predictions B3-B5; (c) chạy `scripts/evaluate_phase5_baselines.py`; (d) đọc paired CI `B5_vs_B2`; (e) viết error analysis. Định nghĩa B0-B5 phải được **khóa trước** khi mở external test mới.
