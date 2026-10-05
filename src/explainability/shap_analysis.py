"""Export model contributions; explanations describe the model, not causality."""
from __future__ import annotations

import json

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

from src.data.common import ROOT, config, write_json
from src.features.preprocessing import features


def run() -> dict:
    bundle = joblib.load(ROOT / "artifacts/models/tabular_v1/bundle.joblib")
    model = bundle["model"]
    frame = pd.read_parquet(ROOT / "data/gold" / config("params.yaml")["gold"]["version"] / "test.parquet")
    x = features(frame)
    transformed = model.named_steps["preprocess"].transform(x)
    transformed = transformed.toarray() if hasattr(transformed, "toarray") else np.asarray(transformed)
    names = model.named_steps["preprocess"].get_feature_names_out()
    estimator = model.named_steps["model"]
    output = ROOT / "artifacts/shap/tabular_v1"
    output.mkdir(parents=True, exist_ok=True)
    if hasattr(estimator, "coef_"):
        # Logistic contributions are exact log-odds terms, not SHAP values.
        contributions = transformed * estimator.coef_[0]
        method = "logistic_log_odds_contributions"
    else:
        explanation = shap.TreeExplainer(estimator)(transformed)
        contributions = explanation.values
        if contributions.ndim == 3:
            contributions = contributions[:, :, 1]
        method = "tree_shap"
    importance = pd.DataFrame({"feature": names, "mean_absolute_contribution": np.abs(contributions).mean(axis=0)}).sort_values("mean_absolute_contribution", ascending=False)
    importance.to_csv(output / "global_importance.csv", index=False)
    local = []
    for row_index, claim_id in enumerate(frame.claim_id):
        top = np.argsort(-np.abs(contributions[row_index]))[:5]
        for rank, column_index in enumerate(top, 1):
            local.append({"claim_id": claim_id, "rank": rank, "feature": names[column_index], "contribution": float(contributions[row_index, column_index]), "direction": "raises model score" if contributions[row_index, column_index] > 0 else "lowers model score"})
    pd.DataFrame(local).to_csv(output / "local_contributions.csv", index=False)
    chart = importance.head(15).iloc[::-1]
    plt.figure(figsize=(10, 6))
    plt.barh(chart.feature, chart.mean_absolute_contribution)
    plt.xlabel("Mean absolute model contribution")
    plt.tight_layout()
    figure = ROOT / "reports/figures/shap_global.png"
    figure.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(figure, dpi=150)
    plt.close()
    metadata = {"method": method, "rows": len(frame), "feature_count": len(names), "warning": "Associations in the model do not establish fraud or causality"}
    write_json(output / "manifest.json", metadata)
    return metadata


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
