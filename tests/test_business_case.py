import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import monte_carlo_business_case as mcbc


def test_canonical_simulation_is_well_formed_and_deterministic():
    res = mcbc.simulate(3000, dec={"N": 20000})
    s = mcbc.summary(res)
    # Binormal shift: AI real Recall@10% median near the worked example (~0.286).
    assert s["Recall_AI"][1] == pytest.approx(0.286, abs=0.02)
    # AI outranks the rule, so its median annual net value is higher.
    assert s["NV_AI"][1] > s["NV_rule"][1]
    # Break-even precision is positive and probabilities are valid.
    assert all(x > 0 for x in s["Prec_star"])
    for key in ("P(NV_AI>0)", "P(dNV>0)", "P(NPV_inc>0)", "P(DPP<=3)", "P(Precision>Prec*)"):
        assert 0.0 <= s[key] <= 1.0


def test_npv_rises_with_claim_volume():
    low = np.median(mcbc.simulate(3000, dec={"N": 10000})["NPV"])
    high = np.median(mcbc.simulate(3000, dec={"N": 50000})["NPV"])
    assert high > low   # larger volume uses the fixed AI cost better


def test_recall_shift_reproduces_worked_example():
    d = mcbc.d_from_test_recall(0.224)
    assert mcbc.recall_at(d, 0.07, 0.10)[0] == pytest.approx(0.286, abs=0.01)
