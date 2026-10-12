# Runbook chạy Colab qua nhiều tài khoản — v1

**Ngày cập nhật:** 12/10/2026

## Kết luận

Có thể chạy từng notebook bằng các tài khoản Colab khác nhau. Model, checkpoint và report được nối bằng thư mục Google Drive dùng chung; chúng không phụ thuộc vào tài khoản đã cấp GPU. Mỗi runtime vẫn phải cài dependency riêng vì `/content` là bộ nhớ tạm của runtime.

## Chuẩn bị tài khoản có GPU

1. Tài khoản sở hữu thư mục chia sẻ `AI_Project_Insurance_Acc 2` cho tài khoản mới với quyền **Editor**.
2. Trong tài khoản mới, mở **Shared with me**, chọn thư mục và **Organize → Add shortcut** vào gốc **My Drive**.
3. Giữ đúng tên shortcut `AI_Project_Insurance_Acc 2` để đường dẫn dưới đây không đổi:

```text
/content/drive/MyDrive/AI_Project_Insurance_Acc 2
```

4. Không chạy đồng thời cùng một notebook/output directory từ hai tài khoản.
5. Không chép checkpoint vào `/content`; chỉ dùng các đường dẫn nằm dưới project trên Drive.

## Preflight bắt buộc

Chạy cell này ngay sau khi mount Drive:

```python
from pathlib import Path
import os, torch

PROJECT = Path("/content/drive/MyDrive/AI_Project_Insurance_Acc 2")
checks = {
    "project_visible": PROJECT.is_dir(),
    "baseline_report": (PROJECT / "reports/metrics/documents/document_baselines_validation_v1.json").is_file(),
    "sroie_split_report": (PROJECT / "reports/data_audit/documents/sroie_processed_split_v1.json").is_file(),
    "sroie_train": (PROJECT / "data/processed/documents/sroie/v1/train.parquet").is_file(),
    "sroie_validation": (PROJECT / "data/processed/documents/sroie/v1/validation.parquet").is_file(),
    "drive_write": os.access(PROJECT, os.W_OK),
    "cuda": torch.cuda.is_available(),
}
print(checks)
if not all(checks.values()):
    raise RuntimeError("Preflight chưa PASS; sửa quyền/shortcut/GPU trước khi train.")
print("GPU:", torch.cuda.get_device_name(0))
```

`no accelerator is found` hoặc `cuda: False` nghĩa là runtime hiện tại không có GPU. Dừng trước phần fine-tune; không để LayoutLMv3 train bằng CPU.

## Thứ tự notebook

| Notebook | Có thể dùng tài khoản nào | Đầu ra dùng chung |
|---|---|---|
| `Document_LayoutLMv3_Candidate_Acc2_v3.ipynb` | Tài khoản bất kỳ còn GPU | `artifacts/document/layoutlmv3_sroie_candidate_v2/` và candidate report v2 |
| `Document_DiT_Independent_Validation_Acc2_v1.ipynb` | Có thể quay lại `hoanganhthu.01230`; GPU khuyến nghị | `reports/metrics/documents/dit_rvl_official_validation_v1.json` |
| `Claim_Consistency_NetworkX_Demo_Acc2_v1.ipynb` | Bất kỳ tài khoản nào; CPU đủ | Report/demo output trên Drive |

Các notebook sau không cần cùng runtime hoặc cùng tài khoản với LayoutLMv3. Chúng chỉ cần đọc được project và các artifact đầu vào đã hoàn tất.

## Khi chuyển lúc notebook CPU đang chạy

- Nếu mới ở bước mount, cài package hoặc alignment: có thể dừng và chạy lại từ đầu ở tài khoản GPU.
- Nếu `trainer.train()` đã bắt đầu bằng CPU: dừng để tránh mất nhiều giờ. Chỉ tiếp tục khi `cuda: True`.
- Không xóa output cũ bằng tay. Notebook v3 dùng output riêng `layoutlmv3_sroie_candidate_v2`; nếu một run hỏng giữa chừng, lưu log và review directory trước khi chạy lại.

