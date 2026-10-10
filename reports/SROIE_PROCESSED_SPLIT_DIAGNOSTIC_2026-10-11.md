# SROIE Processed Split Diagnostic — 2026-10-11

Run đầu đã tạo đúng số dòng dự kiến:

- Raw: 626 train, 361 test.
- Sau loại tám bản train trùng test: 618 dòng.
- Proposed split: 525 train, 93 validation, 361 test.

Verification phát hiện:

```text
train__validation: 1
train__test: 0
validation__test: 0
```

Nguyên nhân là source train còn một nhóm ảnh trùng nội bộ. Thuật toán cũ chia từng row theo key nên hai bản của cùng ảnh rơi sang hai split.

Fix đã áp dụng trong notebook mới:

- Tính SHA-256 của ảnh trong clean train pool.
- Gom mọi row có cùng hash thành một group.
- Dùng deterministic subset-sum với seed `20261011` để chọn nguyên group cho validation và vẫn giữ đúng 93 dòng.
- Xác minh lại cả ba giao train/validation/test phải bằng 0 trước khi ghi lên Drive.

Run lỗi dừng trước bước ghi `OUTPUT_ROOT`, nên không tạo processed artifact không hợp lệ trên Drive.
