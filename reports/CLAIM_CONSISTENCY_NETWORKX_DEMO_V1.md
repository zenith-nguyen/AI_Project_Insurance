# Claim Consistency và NetworkX Demo v1

**Ngày chạy:** 12/10/2026  
**Notebook:** `Claim_Consistency_NetworkX_Demo_Acc2_v1.ipynb`

## Kết quả

Consistency demo: **PASS**.

Point-in-time graph demo: **PASS**.

| Feature | Giá trị demo |
|---|---:|
| `graph_degree` | 1 |
| `shared_entity_count` | 1 |
| `connected_component_size` | 3 |
| `two_hop_claim_count` | 1 |

## Ý nghĩa

Demo xác nhận code dựng graph theo thời điểm, liên kết claim với entity và tính feature cơ bản hoạt động đúng. Consistency rules cũng tạo được kết quả so sánh dữ liệu claim với field chứng từ.

Đây là kiểm thử kỹ thuật trên dữ liệu synthetic, không phải metric phát hiện gian lận. NetworkX là công cụ tạo đặc trưng quan hệ; nó chưa phải fraud model. Muốn đánh giá hiệu quả cần bảng claim/entity/edge thật có `claim_id`, timestamp, provenance và nhãn outcome đáng tin cậy.
