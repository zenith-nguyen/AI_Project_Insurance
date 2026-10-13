# 00 — Hướng dẫn demo Claim Review Workbench trong 5 phút

**Hồ sơ demo:** `CLM-DEMO-SYN-001`  
**URL tổng quan:** `http://127.0.0.1:8000/?claim_id=CLM-DEMO-SYN-001`  
**URL ảnh và chứng từ:** `http://127.0.0.1:8000/?claim_id=CLM-DEMO-SYN-001&tab=evidence`

Ảnh xe do AI tạo; chứng từ, danh tính và quan hệ đều là dữ liệu tổng hợp. Không có dữ liệu khách hàng thật trong hồ sơ demo.

## Trước khi mọi người vào xem

Mở PowerShell tại `D:\AI_Project_Insurance` và chạy:

```powershell
.\.venv\Scripts\python.exe scripts\seed_synthetic_demo.py
powershell -ExecutionPolicy Bypass -File scripts\run_live.ps1
```

Giữ cửa sổ PowerShell mở. Khi thấy server ở `http://127.0.0.1:8000`, mở URL tổng quan trên Edge/Chrome. Nếu server đã chạy thì chỉ cần mở URL và bấm **Phân tích lại**.

## Kịch bản trình bày

1. **Giới thiệu sản phẩm:** “Đây là Claim Review Workbench, màn hình giúp giám định viên gom điểm ưu tiên, ảnh, chứng từ, quan hệ và quyết định vào cùng một `claim_id`.”
2. **Chỉ banner demo:** nói rõ toàn bộ dữ liệu là giả lập và ảnh xe do AI tạo.
3. **Chỉ điểm 75,9/100:** “Đây là điểm xếp hạng nghiên cứu để ưu tiên rà soát, không phải 75,9% xác suất gian lận.”
4. **Chỉ Module nào đã chạy:** XGBoost, relationship, authenticity metadata và consistency đang chạy. Chứng từ dùng field chuẩn bị trước; YOLO và OCR/KIE live chưa bật vì máy này thiếu checkpoint.
5. **Mở Ảnh & chứng từ:** cho xem ảnh xe, giấy sửa xe và trạng thái nguồn gốc ảnh. `Inconclusive` nghĩa là chưa đủ bằng chứng xác nhận ảnh thật hoặc AI.
6. **Mở Quan hệ:** giải thích một entity dùng chung chỉ là tín hiệu cần kiểm tra, không phải kết luận fraud.
7. **Lưu quyết định:** chọn một hướng xử lý, nhập lý do và lưu. Mở tab **Nhật ký** để cho thấy review/correction có audit trail.

## Câu kết thúc

> Nhóm đã hoàn thành Data Audit, Baseline và Evaluation v1. Prototype đã nối risk ranking, bằng chứng, consistency, quan hệ và audit trail trên cùng một claim. Trạng thái hiện tại là Technical PoC; để bàn giao nghiên cứu đầy đủ còn cần checkpoint multimodal trên máy tích hợp, golden run thật và sign-off. Pilot thực tế còn cần dữ liệu bảo hiểm Việt Nam, bảo mật, UAT và monitoring.

## Khi mạng hoặc server gặp sự cố

Mở `04_UI_TONG_QUAN.png` và `05_UI_ANH_CHUNG_TU.png` trong gói báo cáo. Hai ảnh là screenshot từ UI live, đủ để trình bày luồng mà không cần server.

Không nói rằng hệ thống đã “phát hiện chắc chắn gian lận”, “nhận diện chắc chắn ảnh AI”, “đạt KPI nghiệp vụ” hoặc “production-ready”.
