"""Feature policy and train-fitted preprocessing."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.data.common import config


def features(frame: pd.DataFrame) -> pd.DataFrame:
    policy = config("configs/features.yaml")
    result = frame.copy()
    if {"policy_bind_date", "incident_date"}.issubset(result.columns):
        result["policy_age_days"] = (pd.to_datetime(result.incident_date) - pd.to_datetime(result.policy_bind_date)).dt.days
        result.loc[result.policy_age_days < 0, "policy_age_days"] = np.nan
    result = result.drop(columns=[column for column in policy["always_exclude"] if column in result], errors="ignore")
    if any(pd.api.types.is_datetime64_any_dtype(result[column]) for column in result):
        raise ValueError("Unreviewed datetime feature present")
    # sklearn's imputers handle np.nan consistently across pandas versions.
    for column in result.select_dtypes(include=["object", "string", "category"]).columns:
        result[column] = result[column].astype(object).where(result[column].notna(), np.nan)
    return result


def preprocessor(frame: pd.DataFrame, scale_numeric: bool) -> ColumnTransformer:
    numeric = list(frame.select_dtypes(include=["number", "bool"]).columns)
    categorical = [column for column in frame if column not in numeric]
    numeric_steps = [("impute", SimpleImputer(strategy="median", add_indicator=True))]
    if scale_numeric:
        numeric_steps.append(("scale", StandardScaler()))
    categorical_steps = [("impute", SimpleImputer(strategy="constant", fill_value="__UNKNOWN__")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]
    return ColumnTransformer(
        [("numeric", Pipeline(numeric_steps), numeric), ("categorical", Pipeline(categorical_steps), categorical)],
        remainder="drop", sparse_threshold=0.3,
    )
