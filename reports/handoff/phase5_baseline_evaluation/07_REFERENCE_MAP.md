# 07 — Reference map

| Cần đọc | File |
|---|---|
| Baseline ownership | `configs/baseline_registry.v1.yaml` |
| Phase 5 B0–B5 config | `configs/phase5_evaluation.v1.yaml` |
| Gold split và test policy | `README.md`, `data/gold/feature_selection_v1/manifest.json` |
| Feature policy | `configs/features.yaml` |
| Stage feature proposal | `configs/stages.yaml` |
| Rule baseline | `src/baselines/rules.py` |
| Model training | `src/models/train.py` |
| Metric/bootstrap | `src/evaluation/metrics.py` |
| Current tabular results | `reports/RESULTS.md` |
| Feature-policy validation | `reports/FEATURE_POLICY.md` |
| Robustness | `reports/ROBUSTNESS.md` |
| Baseline explanation | `reports/BASELINE_CLARIFICATION_AND_UPGRADE_2026-10-17.md` |
| Model limitation | `docs/handbook/04_MODELS_METRICS_AND_LIMITATIONS.md` |

## Historical numbers for context only

- Frozen test B0 rule: AP 0,424; Recall@10% 16,3%; Precision@10% 40,0%.
- Frozen test XGBoost v1: AP 0,559; Recall@10% 22,4%; Precision@10% 55,0%.
- Train repeated CV: Logistic AP 0,671; XGBoost AP 0,706.
- `val_fs` feature-policy result: research_full AP 0,670; bias-excluded AP 0,598; stage1 AP 0,267; stage3 AP 0,500.

Không đặt các số thuộc CV, val_fs và frozen test vào cùng một hàng rồi tính hiệu số.
