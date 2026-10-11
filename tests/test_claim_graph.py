import pytest

nx = pytest.importorskip("networkx")

from src.graph.claim_graph import build_graph, claim_features


def test_point_in_time_graph_and_features():
    nodes = [
        {"id": "C1", "entity_type": "claim", "available_at": "2026-01-01T00:00:00Z"},
        {"id": "C2", "entity_type": "claim", "available_at": "2026-01-01T00:00:00Z"},
        {"id": "P1", "entity_type": "phone", "available_at": "2026-01-01T00:00:00Z"},
        {"id": "LATE", "entity_type": "phone", "available_at": "2027-01-01T00:00:00Z"},
    ]
    edges = [
        {"source": "C1", "target": "P1", "relation": "uses", "event_time": "2026-01-02T00:00:00Z"},
        {"source": "C2", "target": "P1", "relation": "uses", "event_time": "2026-01-03T00:00:00Z"},
        {"source": "C1", "target": "LATE", "relation": "uses", "event_time": "2027-01-02T00:00:00Z"},
    ]
    graph = build_graph(nodes, edges, "2026-06-01T00:00:00Z")
    features = claim_features(graph, "C1", {"C2"})
    assert "LATE" not in graph
    assert features["shared_entity_count"] == 1
    assert features["two_hop_claim_count"] == 1
    assert features["distance_to_known_risky_claim"] == 2


def test_unknown_claim_is_rejected():
    graph = nx.Graph()
    with pytest.raises(KeyError):
        claim_features(graph, "missing")
