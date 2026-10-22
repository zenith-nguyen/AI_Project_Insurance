# B0 — Khóa quy tắc phá hòa không dùng nhãn

**Sinh bởi:** `python scripts/audit_b0_tie_break.py` → `reports/phase5/b0_tie_break_audit.json`.
**Thay đổi code:** `src/evaluation/metrics.py` thêm `hash_tiebreaker()` và tham số tùy chọn `tie_breaker` cho `top_mask/recall_at_k/precision_at_k` (mặc định giữ nguyên hành vi cũ).

## Vấn đề

Rule baseline B0 chỉ sinh vài giá trị điểm rời rạc. Trên `val_fs`, tại ranh giới hàng đợi top 10% (14/140 hồ sơ):

| Chỉ số | Giá trị |
|---|---:|
| Điểm ranh giới | 1,5 |
| Hồ sơ hòa đúng mức 1,5 | **15** |
| Hồ sơ trên mức ranh giới | 0 |
| **Suất trong hàng đợi do tie-break quyết định** | **14 / 14** |

Tức là **toàn bộ hàng đợi B0 do quy tắc phá hòa quyết định**, không phải do điểm rule. Mặc định `top_mask` phá hòa theo **thứ tự hàng gốc** - một thứ tự tùy tiện, có thể đổi khi dữ liệu được sắp lại và có thể vô tình tương quan với nhãn.

## Mức dao động của metric khi chỉ đổi thứ tự hòa

| Recall@10% | Giá trị |
|---|---:|
| Thứ tự hàng gốc (hiện tại) | 0,1714 |
| Hash claim_id (khóa) | 0,2000 |
| 2.000 lần xáo ngẫu nhiên: min / median / max | 0,1714 / 0,2000 / 0,2000 |

Precision@10% dao động 0,4286 → 0,5000 tương ứng. Một metric mà đổi chỉ vì thứ tự hòa thì không dùng để kết luận được.

## Quy tắc đã khóa

**Khóa secondary key = `sha256(claim_id)` quy về số thực trong [0, 1).**

- **Không dùng nhãn**: chỉ phụ thuộc `claim_id`, không đụng `fraud_label`.
- **Không phụ thuộc thứ tự hàng**: sắp lại dữ liệu vẫn chọn đúng cùng tập hồ sơ.
- **Tái lập**: mọi lần chạy, mọi máy đều ra một kết quả.

```python
from src.evaluation.metrics import hash_tiebreaker, recall_at_k
tb = hash_tiebreaker(frame.claim_id.to_numpy())
recall_at_k(labels, b0_scores, 0.10, tie_breaker=tb)   # ổn định, không dùng nhãn
```

## Lưu ý

- Quy tắc này chỉ **ổn định hóa** việc phá hòa, **không** làm B0 mạnh hơn. Việc B0 có một cụm hòa lớn ở đỉnh cho thấy rule hiện tại gần như không phân biệt được trong nhóm rủi ro cao; đây là lý do giữ B0 làm mốc tham chiếu chứ không phải bộ xếp hạng vận hành.
- Áp dụng cùng một `tie_breaker` cho mọi stage khi so sánh, để so sánh công bằng.
- Thay đổi ở `metrics.py` là **cộng thêm**: `tie_breaker=None` giữ nguyên kết quả cũ, nên các kết quả đã khóa trước đó không bị ảnh hưởng.
