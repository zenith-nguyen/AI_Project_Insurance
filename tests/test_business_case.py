import numpy as np
import pytest

from src.data.common import config
from src.simulation.business_case import shift_recalls, simulate


def test_shift_recalls_vectorized_matches_worked_example():
    out = shift_recalls(np.array([0.224, 0.166]), 0.245, np.array([0.07, 0.07]), k=0.10)
    assert out[0] == pytest.approx(0.286, abs=0.01)   # Thanh Vy's example
    assert out[0] > out[1]                             # higher test recall -> higher real recall


def test_shift_recalls_capped_at_k_over_prevalence():
    out = shift_recalls(np.array([0.40]), 0.245, np.array([0.245]), k=0.10)
    assert out[0] <= 0.10 / 0.245 + 1e-9


def test_simulate_outputs_are_well_formed():
    result = simulate(config("configs/business_case_v2_thanh_vy.yaml"))
    for key in ("nv_ai_annual", "nv_rule_annual", "dnv_annual", "npv", "roi"):
        assert set(result[key]) >= {"mean", "median", "p5", "p95"}
    for prob in result["probabilities"].values():
        assert 0.0 <= prob <= 1.0
    # AI should outrank the rule on recall, so its median annual value exceeds the rule's.
    assert result["nv_ai_annual"]["median"] > result["nv_rule_annual"]["median"]
    assert result["recall_real"]["ai"]["median"] == pytest.approx(0.288, abs=0.02)
