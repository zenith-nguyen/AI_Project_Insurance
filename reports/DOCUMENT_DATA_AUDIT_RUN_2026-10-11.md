# Document Data Audit Run — 2026-10-11

Nguồn: output Colab do nhóm cung cấp từ `Document_Data_Audit_Acc2_v1.ipynb`.

## Kết quả tổng

| Check | Kết quả |
|---|---|
| Registry và manifests | PASS |
| CORD v2 | PASS |
| SROIE structure | PASS |
| SROIE known leakage characterized | PASS |
| FUNSD canonical | PASS |
| XFUND | PASS |
| RVL-CDIP balanced sample | PASS |
| Automated structure valid | True |
| Raw SROIE source split clean | False — expected finding |
| Commercial production gate | Blocked |

## Số liệu

- CORD v2: 800 train, 100 validation, 100 test; decode PASS; không exact duplicate chéo split.
- SROIE: 626 train, 361 test; decode PASS; phát hiện tám exact duplicate train/test.
- FUNSD: chọn canonical root đủ 199 ảnh và 199 annotation; corrupt = 0; ghi nhận một storage tree trùng.
- XFUND: 28 assets; checksum errors = 0; ZIP errors = 0; 1.043 train images, 350 validation images; exact overlap = 0.
- RVL-CDIP: 1.600 ảnh; 16 lớp; mỗi lớp 100 ảnh; hash/decode/balance PASS.

## Tám cặp SROIE train/test trùng tuyệt đối

| Train key | Test key | SHA-256 prefix |
|---|---|---|
| X51005568881 | X51009568881 | 1526ccb2d981 |
| X51006008091 | X51009008091 | 1a0bfb1ade2a |
| X51006332575 | X51006328967 | 1f73b51c8f48 |
| X51005453729 | X51009453729 | 2b97328f51c6 |
| X51006008095 | X51009008095 | 3c867120ac34 |
| X51006329399 | X51006328937 | 489f7ad676d5 |
| X51007135247 | X51006401853 | b20922fadce7 |
| X51006328913 | X51006329388 | f6335f9be62d |

Remediation manifest trên Drive:

```text
/content/drive/MyDrive/AI_Project_Insurance_Acc 2/data/registry/documents/remediation/sroie_source_split_dedup_v1.json
```

Audit JSON và Markdown gốc của run được lưu trong `reports/data_audit/documents/` trên Drive.
