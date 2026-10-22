import numpy as np
import pytest

from src.simulation.montecarlo_roi import (
    choose_operating_point, expected_net_value, mean_param, queue_rates,
    sample_param, simulate_net_value,
)

DISTS = {
    "fraud_loss_avoided": {"dist": "lognormal", "median": 30_000_000, "sigma": 0.5},
    "prevention_effectiveness_manual": {"dist": "beta", "alpha": 5, "beta": 5},
    "prevention_effectiveness_siu": {"dist": "beta", "alpha": 7.5, "beta": 2.5},
    "review_cost": {"dist": "lognormal", "median": 250_000, "sigma": 0.4},
    "siu_cost": {"dist": "lognormal", "median": 2_500_000, "sigma": 0.4},
    "false_hold_cost": {"dist": "uniform", "low": 200_000, "high": 800_000},
    "ai_operation_cost_per_claim": {"dist": "uniform", "low": 2_000, "high": 8_000},
}
POS = np.linspace(0.3, 0.95, 40)
NEG = np.linspace(0.02, 0.6, 120)


def test_mean_param_matches_closed_form():
    assert mean_param({"dist": "beta", "alpha": 5, "beta": 5}) == pytest.approx(0.5)
    assert mean_param({"dist": "uniform", "low": 200_000, "high": 800_000}) == pytest.approx(500_000)
    assert mean_param({"dist": "lognormal", "median": 100, "sigma": 0.4}) == pytest.approx(100 * np.exp(0.08))


def test_queue_rates_are_ordered_and_consistent():
    rates = queue_rates(POS, NEG, 0.4, 0.7, 0.07)
    assert rates["siu_rate"] <= rates["total_review_rate"]
    assert rates["caught_siu"] <= rates["caught_manual"] + rates["caught_siu"]
    assert rates["false_holds"] <= rates["total_review_rate"]
    # A stricter t1 reviews fewer claims.
    assert queue_rates(POS, NEG, 0.6, 0.7, 0.07)["total_review_rate"] <= rates["total_review_rate"]


def test_t2_below_t1_is_rejected():
    with pytest.raises(ValueError):
        queue_rates(POS, NEG, 0.7, 0.4, 0.07)


def test_monte_carlo_mean_converges_to_analytic():
    rates = queue_rates(POS, NEG, 0.4, 0.7, 0.07)
    analytic = expected_net_value(rates, DISTS, 10_000)
    draws = simulate_net_value(rates, DISTS, 10_000, np.random.default_rng(0), 40_000)
    assert float(np.mean(draws)) == pytest.approx(analytic, rel=0.03)


def test_operating_point_respects_capacity_caps():
    best = choose_operating_point(POS, NEG, DISTS, 0.07, 10_000, k1_max=0.20, k2_max=0.05)
    assert best["total_review_rate"] <= 0.20 + 1e-9
    assert best["siu_rate"] <= 0.05 + 1e-9
    assert best["t2"] >= best["t1"]


def test_sample_param_shapes_and_ranges():
    rng = np.random.default_rng(1)
    beta = sample_param({"dist": "beta", "alpha": 2, "beta": 2}, rng, 500)
    assert beta.shape == (500,) and beta.min() >= 0 and beta.max() <= 1
    uni = sample_param({"dist": "uniform", "low": 1, "high": 2}, rng, 500)
    assert uni.min() >= 1 and uni.max() <= 2
