# 05 — Data, artifact và governance

Git chứa source, schema, test, notebook builder và báo cáo. Dữ liệu/version lớn dùng DVC remote; checkpoint dùng artifact store. Người clone repo không mặc nhiên nhận raw data hoặc model bị giới hạn license.

Artifact chính:

```text
artifacts/models/tabular_v1/bundle.joblib
artifacts/models/damage_segmentation/cardd_candidate_v1/best.pt
artifacts/models/document_kie/layoutlmv3_sroie_candidate_v2/checkpoint-264/
```

Hash được khóa tại `configs/model_registry.v1.yaml`. `scripts/setup_live.ps1` chép và kiểm hash; hash sai phải dừng inference.

Quy tắc dữ liệu:

- mọi nguồn trong một hồ sơ phải có cùng `claim_id` và lineage hợp lệ;
- chỉ dùng field tồn tại tại scoring timestamp;
- target `fraud_reported` là observed label, chưa phải verified actual fraud;
- public dataset chỉ phù hợp PoC/benchmark cho đến khi có validation bảo hiểm Việt Nam;
- raw PII, token và dữ liệu hạn chế license không được commit.

