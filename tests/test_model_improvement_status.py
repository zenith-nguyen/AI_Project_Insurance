from pathlib import Path

import yaml

from scripts.render_model_improvement_status import render


ROOT = Path(__file__).resolve().parents[1]


def test_every_improvement_milestone_has_technical_and_business_gates(tmp_path: Path):
    payload = yaml.safe_load((ROOT / "configs/model_improvement_status.v1.yaml").read_text(encoding="utf-8"))
    required = {
        "order", "title", "status", "technical_evidence", "current_metric",
        "business_value", "business_kpi", "gate", "next_action", "blocked_by",
    }
    orders = []
    for item in payload["milestones"].values():
        assert required <= item.keys()
        assert item["status"] in {"complete_engineering", "in_progress", "waiting_for_domain_data"}
        assert all(str(item[key]).strip() for key in required - {"order"})
        orders.append(item["order"])
    assert sorted(orders) == list(range(1, len(orders) + 1))

    output = tmp_path / "status.md"
    content = render(output=output)
    assert output.read_text(encoding="utf-8") == content
    assert "Giá trị nghiệp vụ" in content
    assert "Điều kiện đạt" in content
