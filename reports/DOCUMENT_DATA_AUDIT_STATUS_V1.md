# Document Data Audit Status v1

Ngày cập nhật: 2026-10-11

## Phạm vi đã xác minh

| Nguồn | Trạng thái | Bằng chứng hiện có | Hành động tiếp theo |
|---|---|---|---|
| CORD v2 | PASS cấu trúc và exact leakage | 800 train, 100 validation, 100 test; ảnh decode được; không exact duplicate chéo split | Dùng cho OCR/KIE baseline |
| SROIE corrected mirror | PASS cấu trúc; raw split có leakage | 626 train, 361 test; 8 ảnh trùng tuyệt đối train/test đã được định danh | Giữ test, loại 8 bản train, tạo 93 validation từ train sạch |
| FUNSD | Có hai cây storage cùng chứa bộ 199 mẫu | Lần audit cũ cộng cả hai cây thành 398 ảnh/398 annotation | Audit mới chọn một canonical root 199 ảnh + 199 annotation và ghi nhận storage duplicate |
| XFUND | Intake PASS | 28 release assets, bảy ngôn ngữ | Chạy checksum, ZIP safety và exact leakage audit |
| RVL-CDIP | Sample sẵn sàng | 1.600 ảnh, 16 lớp, 100 ảnh/lớp | Chạy hash/decode/balance audit rồi benchmark classifier |
| MIDV-2020/MIDV-500 | Hoãn theo scope | Metadata/license/checksum đã đăng ký; chưa tải full | Chỉ mở khi bắt đầu nhánh giấy tờ định danh |

## Quy tắc chống leakage

- Không sửa Bronze.
- Giữ nguyên SROIE test 361 mẫu.
- Loại tám bản train trùng test bằng remediation manifest.
- Tạo validation chỉ từ 618 mẫu train sạch, seed `20261011`.
- Processed target: 525 train, 93 validation, 361 test.
- Không dùng test để chọn OCR/KIE model hoặc threshold.

## Trạng thái báo cáo

Kết quả đủ để trình bày rằng nhóm đã thực hiện source registry, manifest audit, image-decode audit, exact-duplicate leakage detection và thiết kế remediation có thể tái lập. Chưa được tuyên bố baseline chứng từ hoàn tất cho đến khi processed split PASS và metric OCR/KIE được tạo.

Audit hoàn chỉnh ngày 2026-10-11 xác nhận CORD, FUNSD canonical, XFUND và RVL-CDIP sample đều PASS. SROIE Processed lần đầu còn một exact duplicate nội bộ bị chia giữa train/validation; thuật toán đã được sửa sang group split theo SHA-256 để giữ toàn bộ bản giống nhau trong cùng một split.
