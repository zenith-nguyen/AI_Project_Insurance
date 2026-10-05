"""Configurable rules fitted on train only."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.data.common import config


class RuleBaseline:
    def __init__(self):
        self.rules = config("configs/rules.yaml")["rules"]
        self.thresholds = {}

    def fit(self, frame: pd.DataFrame):
        for rule in self.rules:
            if rule["op"] == "train_quantile_gte" and rule["feature"] in frame:
                self.thresholds[rule["name"]] = float(pd.to_numeric(frame[rule["feature"]]).quantile(rule["value"]))
        return self

    def score(self, frame: pd.DataFrame) -> np.ndarray:
        result = np.zeros(len(frame), dtype=float)
        for rule in self.rules:
            name, feature, operation = rule["name"], rule["feature"], rule["op"]
            if feature == "policy_age_days" and feature not in frame and {"incident_date", "policy_bind_date"}.issubset(frame):
                values = (pd.to_datetime(frame.incident_date) - pd.to_datetime(frame.policy_bind_date)).dt.days
            elif feature in frame:
                values = frame[feature]
            else:
                raise ValueError(f"Rule {name} requires missing feature {feature}")
            if operation == "train_quantile_gte":
                flag = pd.to_numeric(values).ge(self.thresholds[name])
            elif operation == "lte":
                flag = pd.to_numeric(values).le(rule["value"])
            elif operation == "equals":
                flag = values.astype("string").str.casefold().eq(str(rule["value"]).casefold())
            else:
                raise ValueError(f"Unsupported rule operation: {operation}")
            result += flag.fillna(False).to_numpy(dtype=float) * float(rule["weight"])
        return result
