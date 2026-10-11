from src.integration.consistency import ConsistencyCheck
from src.integration.review import ClaimReviewResult


def test_review_contract_never_auto_decides_claim():
    check = ConsistencyCheck("C1", "amount", "fail", 120, 100, 20, "mismatch", ("D1",))
    payload = ClaimReviewResult("C1", consistency_checks=[check]).to_dict()
    assert payload["decision"] == "human_review"
    assert payload["human_review_required"] is True
    assert payload["summary"]["failed_consistency_checks"] == 1
