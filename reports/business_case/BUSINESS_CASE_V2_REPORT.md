# Business Case & ROI v2 — Monte Carlo trên giả định thật (Thanh Vy)

**Người thực hiện:** Huy Nhật · **Ngày:** 22/10/2026 · **Mô phỏng:** 10.000 lần, seed 2026.
**Sinh bởi:** `python scripts/run_business_case.py` → `reports/business_case/business_case_v2.json` + 3 biểu đồ.

> Giả định tham số (phân phối) là **số thật có nguồn do Thanh Vy cung cấp**. Vài **số cấu trúc** (N hồ sơ/năm, lãi suất chiết khấu, tỷ lệ SIU) là **ước lượng có research**, chờ đối chiếu Mục 5.2 của Thanh Vy. Công thức NV/NPV/ROI/DPP được **tái dựng** từ bảng tham số theo capital budgeting chuẩn (xem mục 2); bản Mục 5.2 gốc có thể khác vài quy ước nhỏ.

## 1. Số cấu trúc (research, ghi nguồn)

| Số | Giá trị dùng | Căn cứ |
|---|---|---|
| N (hồ sơ xe/năm, 1 DN cỡ vừa) | 60.000 | Bồi thường xe DN cỡ vừa ~900 tỷ (MIC ~936 tỷ, PJICO ~880 tỷ, BCTC 2024) ÷ ~15 triệu/vụ (bình quân giả định) |
| Lãi suất chiết khấu | 12%/năm | WACC DN niêm yết VN ~7,6-12% (valueinvesting.io); dùng đầu khung cho đầu tư công nghệ |
| Horizon | 3 năm | Thanh Vy: "cả ba năm dùng chung bộ tham số" |
| Tỷ lệ SIU trong hàng đợi | 10% hàng đợi (~1% tổng hồ sơ) | Giả định vận hành |

## 2. Phương pháp và công thức (tái dựng, minh bạch)

- **Quy đổi Recall theo prevalence (binormal):** điểm nhóm B ~ N(d,1), nhóm A ~ N(0,1); khớp d sao cho Recall@10% ở p_test = 24,5% bằng R_test vừa rút, rồi tính lại Recall@10% ở p thực. **Đã kiểm chứng khớp ví dụ Thanh Vy:** R_test 22,4% → 28,5% ở p=7% (bạn ấy ghi ~28,6%). Không suy d từ ROC-AUC.
- **Tương quan:** R_test,AI và R_test,luật nối bằng **Gaussian copula ρ=0,5** (đo trên cùng 49 hồ sơ).
- **Net value hằng năm (mỗi hệ, so với không làm gì):**
  - Hồ sơ bắt được = p · N · Recall(thực). Lợi ích = bắt được · L̄ · η.
  - Hàng đợi = 10% · N. Chi phí review = hàng đợi · c_bs + (10% hàng đợi) · c_SIU; CSKH = hàng đợi · c_CSKH.
  - Giữ nhầm = hàng đợi − bắt được; chi phí rời bỏ = giữ nhầm · Δq · V_KH.
  - Chi phí AI/năm = GPU + nhân sự AI + giám sát + c_var · N. Chi phí luật/năm = duy trì luật.
  - NV = Lợi ích − review − CSKH − rời bỏ − chi phí vận hành.
- **ΔNV = NV_AI − NV_luật.** NPV = −C₀ + ΔNV · Σ 1/(1+r)^t (t=1..3). ROI = NPV/C₀. DPP = kỳ hoàn vốn chiết khấu (nghịch đảo annuity).

## 3. Kết quả (10.000 lần)

| Đại lượng | p5 | Trung vị | p95 |
|---|---:|---:|---:|
| Recall@10% thực — AI | — | **28,8%** | — |
| Recall@10% thực — luật | — | 19,0% | — |
| ΔNV hằng năm (tỷ VND) | −4,30 | **3,37** | 27,34 |
| NPV 3 năm (tỷ VND) | −11,97 | **6,47** | 64,06 |
| ROI (NPV/C₀) | — | **4,04** | — |
| DPP (năm) | — | 0,31 | — |

**Xác suất đạt tiêu chí quyết định:**
- P(ΔNV > 0) = **0,77**
- P(NPV > 0) = **0,72**
- P(DPP ≤ 3 năm) = **0,72**

Đọc: trường hợp trung vị rất tích cực (NPV +6,5 tỷ, hoàn vốn nhanh), nhưng còn **~28% khả năng NPV âm** (đuôi p5 −12 tỷ) do bất định tổn thất, hiệu quả chặn và tỷ lệ gian lận. Quyết định nên kèm điều kiện (pilot, thu thập nhãn thật) thay vì khẳng định chắc thắng.

![Phân phối NPV](bc_npv_distribution.png)

![Giá trị ròng tăng thêm hằng năm](bc_delta_nv.png)

## 4. Độ nhạy theo N và lãi suất chiết khấu

Hai số research không chắc nhất:

![Độ nhạy N và lãi suất](bc_sensitivity.png)

NPV tăng gần tuyến tính theo N (quy mô càng lớn, lợi ích cố định AI càng được khai thác); lãi suất cao làm NPV giảm nhẹ trong khung 8-16%. Cần N thật và lãi suất của Thanh Vy để chốt con số.

## 5. Giới hạn

1. **Số cấu trúc là research**, chưa phải số Thanh Vy/DN thật: N, lãi suất, tỷ lệ SIU. Thay trong `configs/business_case_v2_thanh_vy.yaml` khi có bản chính thức.
2. **Công thức là tái dựng** theo bảng tham số + capital budgeting chuẩn; Mục 5.2 gốc có thể khác vài quy ước (phạm vi c_CSKH, cách tính SIU...).
3. Recall gốc từ 49 hồ sơ (Jeffreys) và frozen test p=24,5%; tập nhỏ nên bất định lớn.
4. Chưa phải cam kết tài chính; là kịch bản có điều kiện trên giả định.

## 6. Tái lập

```bash
python scripts/run_business_case.py
```
Sửa `configs/business_case_v2_thanh_vy.yaml` (khối `structural` và/hoặc `distributions`) khi có số mới của Thanh Vy.
