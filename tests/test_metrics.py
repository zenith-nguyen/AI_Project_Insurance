import numpy as np
import pytest

from src.evaluation.metrics import paired_stratified_bootstrap, precision_at_k, recall_at_k, stratified_bootstrap, top_mask
from src.evaluation.prevalence import scenario_at_k
from src.evaluation.operations import choose_thresholds, operational_metrics
from src.simulation.net_value import net_value


def test_top_k_uses_ceil_and_stable_ties():
    scores = [0.8, 0.8, 0.1]
    assert top_mask(scores, 0.34).tolist() == [True, True, False]
    assert recall_at_k([1, 0, 1], scores, 0.34) == 0.5
    assert precision_at_k([1, 0, 1], scores, 0.34) == 0.5


def test_scenario_perfect_rank():
    result = scenario_at_k([1, 1, 0, 0], [0.9, 0.8, 0.2, 0.1], 0.1, 0.1)
    assert result["recall_at_k"] == pytest.approx(1.0)
    assert result["precision_at_k"] == pytest.approx(1.0)


def test_bootstrap_is_seeded_and_has_both_classes():
    y = [0, 0, 1, 1, 0, 1]
    scores = [0.1, 0.2, 0.8, 0.9, 0.3, 0.7]
    assert stratified_bootstrap(y, scores, 0.5, samples=30, seed=4) == stratified_bootstrap(y, scores, 0.5, samples=30, seed=4)


def test_paired_bootstrap_reports_candidate_minus_baseline_and_zero_flag():
    y = [1, 1, 1, 0, 0, 0, 0, 0]
    baseline = [0.9, 0.2, 0.1, 0.8, 0.7, 0.6, 0.5, 0.4]
    candidate = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2]
    report = paired_stratified_bootstrap(y, baseline, candidate, 0.5, samples=40, seed=7)
    assert report["average_precision"]["delta"] > 0
    assert report["recall_at_k"]["candidate"] >= report["recall_at_k"]["baseline"]
    assert isinstance(report["average_precision"]["contains_zero"], bool)
    assert report == paired_stratified_bootstrap(y, baseline, candidate, 0.5, samples=40, seed=7)


def test_operational_actions_partition_claims():
    scores = np.arange(100) / 100
    limits = choose_thresholds(scores, 0.1, 0.03)
    rates = operational_metrics(np.array([0] * 80 + [1] * 20), scores, limits)
    assert rates["stp_rate"] + rates["manual_review_rate"] + rates["siu_rate"] == pytest.approx(1)
    assert rates["total_review_rate"] == pytest.approx(0.1)


def test_net_value_requires_actual_business_inputs():
    with pytest.raises(ValueError, match="Business assumptions required"):
        net_value(caught_fraud=1, reviewed=2, siu=1, false_holds=1, total_claims=10)
