"""Train-only descriptive audit; suspicious association is not proof of leakage."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, pointbiserialr

from src.data.common import ROOT, config


def audit(train: pd.DataFrame) -> pd.DataFrame:
    target = train.fraud_label.astype(int)
    policy = config("configs/features.yaml")
    rows = []
    for column in train.columns:
        series = train[column]
        if column == "fraud_label":
            continue
        reason = []
        if column in policy["always_exclude"]:
            reason.append("excluded by temporal/identifier/target policy")
        if column in policy["review_before_use"]:
            reason.append("confirm available at scoring time")
        if series.nunique(dropna=True) > len(series) * 0.8:
            reason.append("high cardinality")
        association = None
        method = None
        if pd.api.types.is_numeric_dtype(series):
            numeric = pd.to_numeric(series, errors="coerce")
            mask = numeric.notna()
            if mask.sum() > 2 and numeric[mask].nunique() > 1:
                association = float(pointbiserialr(target[mask], numeric[mask]).statistic)
                method = "point_biserial"
        elif not pd.api.types.is_datetime64_any_dtype(series):
            table = pd.crosstab(series.fillna("__MISSING__").astype(str), target)
            if 1 < table.shape[0] <= np.sqrt(len(train)) and table.shape[1] == 2:
                chi2 = chi2_contingency(table, correction=False)[0]
                association = float(np.sqrt(chi2 / (len(train) * min(table.shape[0] - 1, 1))))
                method = "cramers_v"
        if association is not None and abs(association) >= 0.8:
            reason.append("very strong target association; investigate provenance")
        rows.append({"column": column, "dtype": str(series.dtype), "missing_rate": float(series.isna().mean()), "n_unique": int(series.nunique(dropna=True)), "cardinality_ratio": float(series.nunique(dropna=True) / len(series)), "association_to_target": association, "association_method": method, "suspicion_reason": "; ".join(reason), "recommended_action": "exclude" if column in policy["always_exclude"] else ("review" if reason else "candidate")})
    return pd.DataFrame(rows)


def write_report(train: pd.DataFrame) -> None:
    output = ROOT / "reports/leakage"
    output.mkdir(parents=True, exist_ok=True)
    report = audit(train)
    report.to_csv(output / "leakage_report.csv", index=False)
    suspicious = report[report.recommended_action != "candidate"]
    text = ["# Train-only feature audit", "", "Association is descriptive; temporal availability and data provenance decide leakage.", "", f"Rows audited: {len(train)}. Flagged columns: {len(suspicious)}.", "", "## Columns needing review", ""]
    text += [f"- `{row.column}`: {row.suspicion_reason}" for row in suspicious.itertuples()]
    amount_fields = [c for c in ["total_claim_amount", "injury_claim", "property_claim", "vehicle_claim"] if c in train]
    if len(amount_fields) == 4:
        residual = pd.to_numeric(train.total_claim_amount) - sum(pd.to_numeric(train[c]) for c in amount_fields[1:])
        text += ["", f"Amount arithmetic exact-match rate: {float((residual == 0).mean()):.3f}."]
    (output / "leakage_summary.md").write_text("\n".join(text) + "\n", encoding="utf-8")
