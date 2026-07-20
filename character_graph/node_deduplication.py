from __future__ import annotations

import re
from dataclasses import dataclass

from .combined_graph import CombinedCharacterGraph, CombinedCharacterNode, CombinedRelationshipEdge, compact


REVIEW_COLUMNS = [
    "Candidate Node",
    "Suggested Type",
    "Matched Canonical Node",
    "Evidence Count",
    "Shared Connections",
    "Source Documents",
    "Review Action",
]
NOISY_NODE_KEYS = {"family", "stone", "students"}


@dataclass(frozen=True)
class DeduplicationCandidate:
    candidate_id: str
    canonical_id: str
    suggested_type: str
    review_action: str


def deduplication_review_rows(
    graph: CombinedCharacterGraph,
    *,
    node_type: str,
) -> list[dict[str, str]]:
    candidates = duplicate_candidates(graph, node_type=node_type)
    return [review_row(graph, candidate) for candidate in candidates]


def node_removal_review_rows(graph: CombinedCharacterGraph) -> list[dict[str, str]]:
    rows = []
    for node_id, node in sorted(graph.characters.items(), key=lambda item: item[1].name.lower()):
        if is_graph_structure_node(node):
            continue
        if not is_low_confidence_node(node):
            continue
        rows.append(
            review_row(
                graph,
                DeduplicationCandidate(
                    candidate_id=node_id,
                    canonical_id="",
                    suggested_type=node.node_type,
                    review_action="hide",
                ),
            )
        )
    return rows


def duplicate_candidates(graph: CombinedCharacterGraph, *, node_type: str) -> list[DeduplicationCandidate]:
    groups: dict[str, list[CombinedCharacterNode]] = {}
    for node in graph.characters.values():
        if node.node_type != node_type:
            continue
        groups.setdefault(deduplication_name_key(node.name, node_type), []).append(node)

    candidates: list[DeduplicationCandidate] = []
    for nodes in groups.values():
        if len(nodes) < 2:
            continue
        ordered = sorted(
            nodes,
            key=lambda node: (
                -node_evidence_count(graph, node.id),
                -node_connection_count(graph, node.id),
                node.name.lower(),
                node.id,
            ),
        )
        canonical = ordered[0]
        for candidate in ordered[1:]:
            candidates.append(
                DeduplicationCandidate(
                    candidate_id=candidate.id,
                    canonical_id=canonical.id,
                    suggested_type=node_type,
                    review_action="alias",
                )
            )
    return sorted(candidates, key=lambda item: (graph.characters[item.candidate_id].name.lower(), item.candidate_id))


def deduplication_review_graph(
    graph: CombinedCharacterGraph,
    rows: list[dict[str, str]],
) -> CombinedCharacterGraph:
    candidate_names = {row["Candidate Node"] for row in rows}
    canonical_names = {row["Matched Canonical Node"] for row in rows if row["Matched Canonical Node"]}
    review_ids = {
        node_id
        for node_id, node in graph.characters.items()
        if node.name in candidate_names or node.name in canonical_names
    }
    visible_ids = set(review_ids)
    for edge in graph.edges:
        if edge.source in review_ids:
            visible_ids.add(edge.target)
        if edge.target in review_ids:
            visible_ids.add(edge.source)
    visible_nodes = {
        node_id: node
        for node_id, node in graph.characters.items()
        if node_id in visible_ids and not is_graph_structure_node(node)
    }
    return CombinedCharacterGraph(
        characters=visible_nodes,
        edges=[
            edge
            for edge in graph.edges
            if edge.source in visible_nodes and edge.target in visible_nodes
        ],
    )


def review_row(graph: CombinedCharacterGraph, candidate: DeduplicationCandidate) -> dict[str, str]:
    candidate_node = graph.characters[candidate.candidate_id]
    canonical_node = graph.characters.get(candidate.canonical_id)
    shared = shared_connection_names(graph, candidate.candidate_id, candidate.canonical_id)
    return {
        "Candidate Node": candidate_node.name,
        "Suggested Type": candidate.suggested_type.title(),
        "Matched Canonical Node": canonical_node.name if canonical_node else "",
        "Evidence Count": str(node_evidence_count(graph, candidate.candidate_id)),
        "Shared Connections": ", ".join(shared),
        "Source Documents": ", ".join(source_document_names(graph, candidate.candidate_id)),
        "Review Action": candidate.review_action,
    }


def deduplication_name_key(name: str, node_type: str) -> str:
    normalized = re.sub(r"['’]", "", name.lower())
    normalized = re.sub(r"[^a-z0-9]+", "", normalized)
    if node_type in {"group", "family"} and normalized.endswith("s"):
        normalized = normalized[:-1]
    return normalized


def node_evidence_count(graph: CombinedCharacterGraph, node_id: str) -> int:
    return sum(len(edge.evidence) for edge in graph.edges if node_id in {edge.source, edge.target})


def node_connection_count(graph: CombinedCharacterGraph, node_id: str) -> int:
    return sum(1 for edge in graph.edges if node_id in {edge.source, edge.target})


def shared_connection_names(graph: CombinedCharacterGraph, candidate_id: str, canonical_id: str) -> list[str]:
    if not candidate_id or not canonical_id:
        return []
    candidate_connections = adjacent_node_ids(graph, candidate_id)
    canonical_connections = adjacent_node_ids(graph, canonical_id)
    return sorted(
        {
            graph.characters[node_id].name
            for node_id in candidate_connections & canonical_connections
            if node_id in graph.characters and not is_graph_structure_node(graph.characters[node_id])
        }
    )


def source_document_names(graph: CombinedCharacterGraph, node_id: str) -> list[str]:
    sources = []
    for edge in graph.edges:
        if edge.source == node_id:
            adjacent = graph.characters.get(edge.target)
        elif edge.target == node_id:
            adjacent = graph.characters.get(edge.source)
        else:
            continue
        if adjacent is not None and adjacent.node_type == "source_document":
            sources.append(adjacent.name)
    return sorted(dict.fromkeys(sources))


def adjacent_node_ids(graph: CombinedCharacterGraph, node_id: str) -> set[str]:
    adjacent = set()
    for edge in graph.edges:
        if edge.source == node_id:
            adjacent.add(edge.target)
        elif edge.target == node_id:
            adjacent.add(edge.source)
    return adjacent


def is_low_confidence_node(node: CombinedCharacterNode) -> bool:
    return compact(node.name) in NOISY_NODE_KEYS or compact(node.id) in NOISY_NODE_KEYS


def is_graph_structure_node(node: CombinedCharacterNode) -> bool:
    return node.node_type == "source_document" or node.node_type.startswith("source_heading")
