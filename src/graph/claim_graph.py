"""NetworkX baseline for explainable, point-in-time claim graph features."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable
import re
import unicodedata


def normalize_entity(entity_type: str, value: Any) -> str:
    """Normalize formatting variants without doing fuzzy identity guessing."""
    raw = unicodedata.normalize("NFKD", str(value).strip())
    ascii_value = "".join(char for char in raw if not unicodedata.combining(char)).upper().replace("Đ", "D")
    if entity_type in {"contact_phone", "phone", "telephone"}:
        digits = re.sub(r"\D", "", ascii_value)
        if digits.startswith("0084"):
            digits = digits[2:]
        if digits.startswith("84") and len(digits) in {11, 12}:
            digits = "0" + digits[2:]
        return digits
    return re.sub(r"[^A-Z0-9]", "", ascii_value)


def _time(value: str | datetime) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def build_graph(nodes: Iterable[dict[str, Any]], edges: Iterable[dict[str, Any]], scored_at: str | datetime):
    try:
        import networkx as nx
    except ImportError as error:
        raise RuntimeError("NetworkX is required; install requirements-document.txt.") from error
    cutoff = _time(scored_at)
    graph = nx.Graph(scored_at=cutoff.isoformat())
    for node in nodes:
        node_id = str(node["id"])
        available_at = _time(node["available_at"])
        if available_at <= cutoff:
            graph.add_node(node_id, **node)
    for edge in edges:
        source, target = str(edge["source"]), str(edge["target"])
        event_time = _time(edge["event_time"])
        if event_time <= cutoff and source in graph and target in graph:
            graph.add_edge(source, target, **edge)
    return graph


def claim_features(graph, claim_id: str, known_risky_claims: set[str] | None = None) -> dict[str, float | int | None]:
    try:
        import networkx as nx
    except ImportError as error:
        raise RuntimeError("NetworkX is required; install requirements-document.txt.") from error
    if claim_id not in graph or graph.nodes[claim_id].get("entity_type") != "claim":
        raise KeyError(f"Unknown claim node: {claim_id}")
    neighbors = list(graph.neighbors(claim_id))
    shared_entity_count = sum(graph.degree(entity) > 1 for entity in neighbors)
    component = nx.node_connected_component(graph, claim_id)
    risky_distances = []
    for risky_claim in known_risky_claims or set():
        if risky_claim != claim_id and risky_claim in component:
            risky_distances.append(nx.shortest_path_length(graph, claim_id, risky_claim))
    cycle_count = sum(claim_id in cycle for cycle in nx.cycle_basis(graph.subgraph(component)))
    two_hop_claims = {
        node
        for entity in neighbors
        for node in graph.neighbors(entity)
        if node != claim_id and graph.nodes[node].get("entity_type") == "claim"
    }
    return {
        "graph_degree": graph.degree(claim_id),
        "shared_entity_count": shared_entity_count,
        "connected_component_size": len(component),
        "two_hop_claim_count": len(two_hop_claims),
        "cycle_count": cycle_count,
        "distance_to_known_risky_claim": min(risky_distances) if risky_distances else None,
    }
