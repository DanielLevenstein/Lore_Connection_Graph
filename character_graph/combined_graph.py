from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from difflib import SequenceMatcher
from pathlib import Path

from .schema import CharacterGraph


PRESERVED_RELATIONSHIP_TYPES = {
    "ally",
    "enemy",
    "lover",
    "rival",
    "betrayer",
    "client",
    "family",
    "mentor",
}

CANONICAL_SESSION_NAME_VARIANTS = {
    "dizlevad": {"Dizelvad"},
    "morningstar": {"Moningstar"},
    "sauriv": {"Sauriv-Isk", "Surriv"},
    "typhon": {"Typheb", "Typhen", "Typhin"},
}
MAX_FOCUSED_GRAPH_CONNECTIONS = 6


@dataclass(frozen=True)
class CombinedCharacterNode:
    id: str
    name: str
    source_file: str
    node_type: str = "character"


@dataclass
class CombinedRelationshipEdge:
    source: str
    target: str
    relationship_type: str
    relationship_label: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class CombinedCharacterGraph:
    characters: dict[str, CombinedCharacterNode] = field(default_factory=dict)
    edges: list[CombinedRelationshipEdge] = field(default_factory=list)


@dataclass(frozen=True)
class GraphClarityMetric:
    score: int
    grade: str
    node_count: int
    edge_count: int
    max_outgoing_edges: int
    edge_density: float


def build_combined_character_graph(
    graphs: list[CharacterGraph],
    place_sources: list[tuple[str, str, str]] | None = None,
    lore_relationships: list[dict[str, str]] | None = None,
) -> CombinedCharacterGraph:
    combined = CombinedCharacterGraph()
    for graph in graphs:
        session_note_graph = is_session_note_graph(graph)
        combined.characters[graph.primary_character.id] = CombinedCharacterNode(
            id=graph.primary_character.id,
            name=combined_primary_display_name(graph, session_note_graph),
            source_file=graph.primary_character.source_file,
            node_type=combined_primary_node_type(graph, session_note_graph),
        )
        if not session_note_graph:
            for character_id, character in graph.characters.items():
                combined.characters.setdefault(
                    character_id,
                    CombinedCharacterNode(
                        id=character_id,
                        name=display_name(character.name),
                        source_file=graph.primary_character.source_file,
                        node_type="character",
                    ),
                )
        for place_id, place in graph.places.items():
            combined.characters.setdefault(
                place_id,
                CombinedCharacterNode(
                    id=place_id,
                    name=display_name(place.name),
                    source_file=graph.primary_character.source_file,
                    node_type="place",
                ),
            )
        if not session_note_graph:
            for attribute_id, attribute in graph.attributes.items():
                if attribute.attribute_type.lower() != "family":
                    continue
                combined.characters.setdefault(
                    attribute_id,
                    CombinedCharacterNode(
                        id=attribute_id,
                        name=family_display_name(attribute.value),
                        source_file=graph.primary_character.source_file,
                        node_type="family",
                    ),
                )
    for place_id, place_name, source_file in place_sources or []:
        combined.characters[place_id] = CombinedCharacterNode(
            id=place_id,
            name=display_name(place_name),
            source_file=source_file,
            node_type="place",
        )
    for relationship in lore_relationships or []:
        source_id = relationship.get("source_id", "")
        target_id = relationship.get("target_id", "")
        if not source_id or not target_id:
            continue
        combined.characters.setdefault(
            source_id,
            CombinedCharacterNode(
                id=source_id,
                name=display_name(relationship.get("source_name", source_id)),
                source_file=relationship.get("source_file", ""),
                node_type=combined_lore_node_type(
                    relationship.get("source_name", source_id),
                    relationship.get("source_file", ""),
                    relationship.get("source_type", "place"),
                ),
            ),
        )
        combined.characters.setdefault(
            target_id,
            CombinedCharacterNode(
                id=target_id,
                name=display_name(relationship.get("target_name", target_id)),
                source_file=relationship.get("target_file", relationship.get("source_file", "")),
                node_type=combined_lore_node_type(
                    relationship.get("target_name", target_id),
                    relationship.get("target_file", relationship.get("source_file", "")),
                    relationship.get("target_type", "character"),
                ),
            ),
        )
    by_key: dict[tuple[str, str, str], CombinedRelationshipEdge] = {}

    for graph in graphs:
        session_note_graph = is_session_note_graph(graph)
        source_id = graph.primary_character.id
        for relationship in graph.relationships:
            if session_note_graph and relationship.relationship_type != "place":
                continue
            target_is_family = (
                relationship.target in graph.attributes
                and graph.attributes[relationship.target].attribute_type.lower() == "family"
            )
            if relationship.target in graph.attributes and not target_is_family:
                continue
            target_node = graph.characters.get(relationship.target) or graph.places.get(relationship.target)
            if target_is_family:
                target_node = graph.attributes.get(relationship.target)
            if target_node is None:
                continue
            if relationship.target in graph.characters and not target_is_family:
                matched_primary_id = match_primary_character(
                    target_node.name,
                    relationship.evidence,
                    primary_character_nodes(combined.characters),
                    source_id,
                ) or relationship.target
            else:
                matched_primary_id = relationship.target
            if source_id == matched_primary_id:
                continue
            relationship_type, relationship_label = combined_relationship_type(relationship.relationship_type)
            key = (source_id, matched_primary_id, relationship_type)
            edge = by_key.get(key)
            if edge is None:
                edge = CombinedRelationshipEdge(
                    source=source_id,
                    target=matched_primary_id,
                    relationship_type=relationship_type,
                    relationship_label=relationship_label,
                    evidence=[],
                )
                by_key[key] = edge
                combined.edges.append(edge)
            for evidence in relationship.evidence:
                if evidence and evidence not in edge.evidence:
                    edge.evidence.append(evidence)

    for relationship in lore_relationships or []:
        source_id = relationship.get("source_id", "")
        target_id = relationship.get("target_id", "")
        if not source_id or not target_id or source_id == target_id:
            continue
        relationship_type = one_word_relationship(relationship.get("relationship", "reference"))
        relationship_label = relationship_display_label(relationship_type)
        key = (source_id, target_id, relationship_type)
        edge = by_key.get(key)
        if edge is None:
            edge = CombinedRelationshipEdge(
                source=source_id,
                target=target_id,
                relationship_type=relationship_type,
                relationship_label=relationship_label,
                evidence=[],
            )
            by_key[key] = edge
            combined.edges.append(edge)
        evidence = relationship.get("evidence", "")
        if evidence and evidence not in edge.evidence:
            edge.evidence.append(evidence)

    merge_duplicate_nodes(combined)
    prune_disconnected_nodes(combined)
    clarify_duplicate_display_names(combined)
    return combined


def is_session_note_graph(graph: CharacterGraph) -> bool:
    source_file = graph.primary_character.source_file.replace("\\", "/").lower()
    source_name = source_file.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    primary_id = compact(graph.primary_character.id)
    primary_name = compact(graph.primary_character.name)
    return (
        "/session_notes/" in source_file
        or source_file.endswith("/session_notes.md")
        or compact(source_name) in {"sessionnote", "sessionnotes"}
        or primary_id in {"sessionnote", "sessionnotes"}
        or primary_name in {"sessionnote", "sessionnotes"}
    )


def combined_primary_display_name(graph: CharacterGraph, session_note_graph: bool) -> str:
    if not session_note_graph:
        return display_name(graph.primary_character.name)
    source_file = graph.primary_character.source_file.replace("\\", "/")
    source_name = source_file.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    if compact(source_name) in {"sessionnote", "sessionnotes"}:
        return "Session Notes"
    return display_name(source_name) or display_name(graph.primary_character.name)


def combined_primary_node_type(graph: CharacterGraph, session_note_graph: bool) -> str:
    if session_note_graph and is_named_session_source(graph.primary_character.name, graph.primary_character.source_file):
        return "source_document"
    return "character"


def combined_lore_node_type(name: str, source_file: str, fallback_type: str) -> str:
    if is_named_session_source(name, source_file):
        return "source_document"
    return fallback_type


def family_display_name(value: str) -> str:
    name = display_name(value).strip()
    return name if compact(name).endswith("family") else f"{name} Family"


def is_named_session_source(name: str, source_file: str) -> bool:
    normalized_source = source_file.replace("\\", "/").lower()
    source_name = normalized_source.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    if "/session_notes/" not in normalized_source and not normalized_source.endswith("/session_notes.md"):
        return False
    source_key = compact(source_name)
    return source_key not in {"sessionnote", "sessionnotes"} and compact(name) == source_key


def merge_duplicate_nodes(graph: CombinedCharacterGraph) -> None:
    canonical_by_key: dict[tuple[str, str], str] = {}
    remapped_ids: dict[str, str] = {}
    for node_id, node in graph.characters.items():
        key = (node.node_type, compact(node.name))
        canonical_id = canonical_by_key.setdefault(key, node_id)
        if canonical_id != node_id:
            remapped_ids[node_id] = canonical_id
    if not remapped_ids:
        return
    graph.characters = {
        node_id: node
        for node_id, node in graph.characters.items()
        if node_id not in remapped_ids
    }
    for edge in graph.edges:
        edge.source = remapped_ids.get(edge.source, edge.source)
        edge.target = remapped_ids.get(edge.target, edge.target)
    dedupe_combined_edges(graph)


def dedupe_combined_edges(graph: CombinedCharacterGraph) -> None:
    deduped: list[CombinedRelationshipEdge] = []
    by_key: dict[tuple[str, str, str], CombinedRelationshipEdge] = {}
    for edge in graph.edges:
        if edge.source == edge.target:
            continue
        key = (edge.source, edge.target, edge.relationship_type)
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = edge
            deduped.append(edge)
            continue
        for evidence in edge.evidence:
            if evidence and evidence not in existing.evidence:
                existing.evidence.append(evidence)
    graph.edges = deduped


def clarify_duplicate_display_names(graph: CombinedCharacterGraph) -> None:
    ids_by_name: dict[str, list[str]] = {}
    for node_id, node in graph.characters.items():
        ids_by_name.setdefault(compact(node.name), []).append(node_id)
    for node_ids in ids_by_name.values():
        if len(node_ids) < 2:
            continue
        for node_id in node_ids:
            node = graph.characters[node_id]
            graph.characters[node_id] = replace(node, name=f"{node.name} ({node.node_type.title()})")


def prune_disconnected_nodes(graph: CombinedCharacterGraph) -> None:
    connected_ids = {edge.source for edge in graph.edges} | {edge.target for edge in graph.edges}
    graph.characters = {
        node_id: node
        for node_id, node in graph.characters.items()
        if node_id in connected_ids
    }


def primary_character_nodes(nodes: dict[str, CombinedCharacterNode]) -> dict[str, CombinedCharacterNode]:
    return {node_id: node for node_id, node in nodes.items() if node.node_type == "character"}


def match_primary_character(
    candidate_name: str,
    evidence: list[str],
    primaries: dict[str, CombinedCharacterNode],
    source_id: str,
) -> str:
    text = " ".join([candidate_name, *evidence])
    compact_text = compact(text)
    best_match = ""
    best_score = 0.0
    for primary_id, primary in primaries.items():
        if primary_id == source_id:
            continue
        aliases = primary_aliases(primary.name)
        if any(alias and alias in compact_text for alias in aliases):
            return primary_id
        score = fuzzy_name_score(candidate_name, primary.name)
        if score > best_score:
            best_match = primary_id
            best_score = score
    return best_match if best_score >= 0.82 else ""


def primary_aliases(name: str) -> set[str]:
    parts = [part for part in re.split(r"\s+", name.strip()) if part]
    aliases = {compact(name)}
    if len(parts) > 1 and compact(parts[-1]) not in {"mother", "father", "parent", "child"}:
        aliases.add(compact(parts[-1]))
    return aliases


def fuzzy_name_score(candidate_name: str, primary_name: str) -> float:
    candidate_parts = [part for part in re.split(r"\s+", candidate_name.strip()) if part]
    primary_parts = [part for part in re.split(r"\s+", primary_name.strip()) if part]
    if not candidate_parts or not primary_parts:
        return 0.0
    if compact(candidate_parts[0]) != compact(primary_parts[0]):
        return 0.0
    return SequenceMatcher(None, compact(candidate_name), compact(primary_name)).ratio()


def combined_relationship_type(relationship_type: str) -> tuple[str, str]:
    if relationship_type in PRESERVED_RELATIONSHIP_TYPES:
        return relationship_type, relationship_display_label(relationship_type)
    if relationship_type == "place":
        return "place", "Place"
    return "reference", "Referenced"


def relationship_display_label(relationship_type: str) -> str:
    if relationship_type == "rival":
        return "Rivals"
    return relationship_type.replace("_", " ").title()


def one_word_relationship(value: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", value.lower())
    return words[0] if words else "reference"


def combined_relationship_rows(graph: CombinedCharacterGraph) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for edge in graph.edges:
        source = graph.characters.get(edge.source)
        target = graph.characters.get(edge.target)
        for evidence in edge.evidence or [""]:
            rows.append(
                {
                    "Character": source.name if source else edge.source,
                    "Character Type": source.node_type.title() if source else "",
                    "Relationship": edge.relationship_label,
                    "Connection": target.name if target else edge.target,
                    "Connection Type": target.node_type.title() if target else "",
                    "Evidence": compact_evidence([evidence]),
                }
            )
    return rows


def combined_attribute_rows(graphs: list[CharacterGraph]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for graph in graphs:
        primary_name = display_name(graph.primary_character.name)
        for attribute in graph.attributes.values():
            if attribute.attribute_type.lower() == "family":
                continue
            rows.append(
                {
                    "Character": primary_name,
                    "Attribute": attribute.attribute_type,
                    "Value": display_name(attribute.value),
                    "Evidence": compact_evidence(attribute.source_spans),
                }
            )
    return rows


def combined_node_detail_rows(graph: CombinedCharacterGraph, node_id: str) -> list[dict[str, str]]:
    node = graph.characters.get(node_id)
    if node is None:
        return []

    rows = [
        {
            "Detail": "Node",
            "Relationship": "",
            "Value": node.name,
            "Type": node.node_type.title(),
            "Evidence": source_file_label(node.source_file),
        }
    ]
    for edge in graph.edges:
        source = graph.characters.get(edge.source)
        target = graph.characters.get(edge.target)
        if edge.source == node_id and target is not None:
            rows.append(
                {
                    "Detail": "Outgoing",
                    "Relationship": edge.relationship_label,
                    "Value": target.name,
                    "Type": target.node_type.title(),
                    "Evidence": compact_evidence(edge.evidence),
                }
            )
        elif edge.target == node_id and source is not None:
            rows.append(
                {
                    "Detail": "Incoming",
                    "Relationship": edge.relationship_label,
                    "Value": source.name,
                    "Type": source.node_type.title(),
                    "Evidence": compact_evidence(edge.evidence),
                }
            )
    return rows


def source_file_label(source_file: str) -> str:
    if not source_file:
        return ""
    name = Path(source_file).name
    return f"Source: {name}" if name else ""


def focused_combined_graph(graph: CombinedCharacterGraph, node_id: str) -> CombinedCharacterGraph:
    if node_id not in graph.characters:
        return graph
    focused_edges = [
        edge
        for edge in graph.edges
        if edge.source == node_id or edge.target == node_id
    ]
    focused_ids = {node_id} | {edge.source for edge in focused_edges} | {edge.target for edge in focused_edges}
    return CombinedCharacterGraph(
        characters={
            current_id: node
            for current_id, node in graph.characters.items()
            if current_id in focused_ids
        },
        edges=focused_edges,
    )


def graph_view_root_nodes(
    graph: CombinedCharacterGraph,
    main_character_names: list[str] | None = None,
    main_place_names: list[str] | None = None,
) -> list[CombinedCharacterNode]:
    main_character_ids = {compact(name) for name in main_character_names or []}
    main_place_ids = {compact(name) for name in main_place_names or []}
    nodes = [node for node in graph.characters.values() if node.node_type in {"character", "place", "source_document"}]
    main_nodes = [
        node
        for node in nodes
        if not is_session_notes_node(node)
        and (
            (
                node.node_type == "character"
                and (compact(node.name) in main_character_ids or node.id in main_character_ids)
            )
            or (
                node.node_type in {"place", "source_document"}
                and (compact(node.name) in main_place_ids or node.id in main_place_ids)
            )
        )
    ]
    weights = node_mention_weights(graph.edges)
    return sorted(main_nodes, key=lambda node: (-weights.get(node.id, 0), node.node_type, node.name.lower()))


def other_connections_graph(graph: CombinedCharacterGraph, node_id: str) -> CombinedCharacterGraph:
    node = graph.characters.get(node_id)
    if node is None:
        return graph
    associated = associated_connection_items(graph, node_id)
    return CombinedCharacterGraph(
        characters={
            node_id: node,
            **{associated_node.id: associated_node for associated_node, _evidence in associated},
        },
        edges=[
            prominent_edge_for_association(graph, node_id, associated_node.id, evidence)
            for associated_node, evidence in associated
        ],
    )


def party_connections_graph(graph: CombinedCharacterGraph, root_node_ids: list[str]) -> CombinedCharacterGraph:
    root_ids = [node_id for node_id in root_node_ids if node_id in graph.characters]
    root_id_set = set(root_ids)
    if not root_ids:
        return CombinedCharacterGraph()
    characters = {
        node_id: graph.characters[node_id]
        for node_id in root_ids
    }
    edges: list[CombinedRelationshipEdge] = []
    edge_keys: set[tuple[str, str]] = set()
    for root_id in root_ids:
        for associated_node, evidence in associated_connection_items(graph, root_id):
            if associated_node.id in root_id_set and associated_node.id != root_id:
                target_id = associated_node.id
            elif associated_node.id in root_id_set:
                continue
            else:
                target_id = associated_node.id
            characters[target_id] = associated_node
            key = (root_id, target_id)
            if key in edge_keys:
                continue
            edge_keys.add(key)
            edges.append(
                prominent_edge_for_association(
                    graph,
                    root_id,
                    target_id,
                    evidence,
                )
            )
    return CombinedCharacterGraph(characters=characters, edges=edges)


def prominent_edge_for_association(
    graph: CombinedCharacterGraph,
    source_id: str,
    target_id: str,
    evidence: list[str],
) -> CombinedRelationshipEdge:
    relationship_type, relationship_label = prominent_relationship_between(graph, source_id, target_id)
    return CombinedRelationshipEdge(
        source=source_id,
        target=target_id,
        relationship_type=relationship_type,
        relationship_label=relationship_label,
        evidence=evidence,
    )


def prominent_relationship_between(
    graph: CombinedCharacterGraph,
    source_id: str,
    target_id: str,
) -> tuple[str, str]:
    candidates = [
        edge
        for edge in graph.edges
        if {edge.source, edge.target} == {source_id, target_id}
    ]
    candidates.extend(indirect_lore_source_edges_for_association(graph, source_id, target_id))
    if not candidates:
        candidates = session_source_edges_for_association(graph, source_id, target_id)
    if not candidates:
        return "connected", "Connected"
    prominent = sorted(
        candidates,
        key=lambda edge: (
            -len(edge.evidence),
            relationship_prominence_rank(edge.relationship_type),
            edge.relationship_label.lower(),
        ),
    )[0]
    return prominent.relationship_type, prominent.relationship_label


def session_source_edges_for_association(
    graph: CombinedCharacterGraph,
    source_id: str,
    target_id: str,
) -> list[CombinedRelationshipEdge]:
    session_ids = {
        edge.source
        for edge in graph.edges
        if edge.target == source_id and is_lore_source_node(graph.characters.get(edge.source))
    }
    session_ids.update(
        edge.target
        for edge in graph.edges
        if edge.source == source_id and is_lore_source_node(graph.characters.get(edge.target))
    )
    return [
        edge
        for edge in graph.edges
        if (
            (edge.source in session_ids and edge.target == target_id)
            or (edge.target in session_ids and edge.source == target_id)
        )
    ]


def indirect_lore_source_edges_for_association(
    graph: CombinedCharacterGraph,
    source_id: str,
    target_id: str,
) -> list[CombinedRelationshipEdge]:
    target_node = graph.characters.get(target_id)
    if not is_lore_source_node(target_node):
        return []
    family_ids = directly_associated_family_node_ids(graph, source_id)
    return [
        edge
        for edge in graph.edges
        if (
            (edge.source == target_id and edge.target in family_ids)
            or (edge.target == target_id and edge.source in family_ids)
        )
    ]


def relationship_prominence_rank(relationship_type: str) -> int:
    ranks = {
        "family": 0,
        "lover": 1,
        "betrayer": 2,
        "enemy": 3,
        "rival": 4,
        "mentor": 5,
        "ally": 6,
        "client": 7,
        "place": 8,
        "location": 8,
        "home": 8,
        "visited": 9,
        "mentioned": 10,
        "reference": 11,
        "connected": 12,
    }
    return ranks.get(relationship_type, 9)


def full_character_connection_graph(graph: CombinedCharacterGraph) -> CombinedCharacterGraph:
    characters = {
        node_id: node
        for node_id, node in graph.characters.items()
        if not is_session_notes_node(node)
    }
    edges = [
        edge
        for edge in graph.edges
        if edge.source in characters and edge.target in characters
    ]
    return CombinedCharacterGraph(characters=characters, edges=edges)


def other_connection_rows(graph: CombinedCharacterGraph, node_id: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for associated_node, evidence_items in associated_connection_items(graph, node_id):
        for evidence in evidence_items or [""]:
            rows.append(
                {
                    "Connection": associated_node.name,
                    "Type": associated_node.node_type.title(),
                    "Evidence": compact_evidence([evidence]),
                }
            )
    return rows


def associated_connection_items(
    graph: CombinedCharacterGraph,
    node_id: str,
    max_items: int = MAX_FOCUSED_GRAPH_CONNECTIONS,
) -> list[tuple[CombinedCharacterNode, list[str]]]:
    node = graph.characters.get(node_id)
    if node is None:
        return []
    associated_ids = directly_associated_node_ids(graph, node_id)
    associated_ids.update(session_sibling_node_ids(graph, node_id))
    associated_ids.update(indirect_lore_source_node_ids(graph, node_id))
    associated_ids.discard(node_id)
    associated = [
        graph.characters[associated_id]
        for associated_id in associated_ids
        if associated_id in graph.characters
        and graph.characters[associated_id].node_type in {"character", "place", "family", "group", "source_document"}
        and not is_session_notes_node(graph.characters[associated_id])
    ]
    items: list[tuple[CombinedCharacterNode, list[str]]] = []
    weights = node_mention_weights(graph.edges)
    for associated_node in sorted(associated, key=lambda item: association_sort_key(graph, node_id, item, weights)):
        evidence = evidence_between_or_from_source(graph, node_id, associated_node.id)
        if not evidence:
            continue
        items.append((associated_node, evidence))
    if len(items) <= max_items:
        return items
    protected_items = [
        item
        for item in items
        if item[0].node_type in {"family", "group", "source_document"}
    ]
    remaining_items = [item for item in items if item not in protected_items]
    return protected_items + remaining_items[: max(max_items - len(protected_items), 0)]


def association_sort_key(
    graph: CombinedCharacterGraph,
    node_id: str,
    associated_node: CombinedCharacterNode,
    weights: dict[str, int],
) -> tuple[int, int, int, int, str]:
    relationship_type, _relationship_label = prominent_relationship_between(graph, node_id, associated_node.id)
    direct = associated_node.id in directly_associated_node_ids(graph, node_id)
    type_rank = {
        "family": 0,
        "source_document": 1,
        "character": 2,
        "place": 3,
        "group": 4,
    }.get(associated_node.node_type, 5)
    return (
        0 if direct else 1,
        relationship_prominence_rank(relationship_type),
        type_rank,
        -weights.get(associated_node.id, 0),
        associated_node.name.lower(),
    )


def directly_associated_node_ids(graph: CombinedCharacterGraph, node_id: str) -> set[str]:
    associated: set[str] = set()
    for edge in graph.edges:
        if edge.source == node_id:
            associated.add(edge.target)
        elif edge.target == node_id:
            associated.add(edge.source)
    return associated


def indirect_lore_source_node_ids(graph: CombinedCharacterGraph, node_id: str) -> set[str]:
    family_ids = directly_associated_family_node_ids(graph, node_id)
    if not family_ids:
        return set()
    source_ids: set[str] = set()
    for edge in graph.edges:
        if edge.target in family_ids and is_lore_source_node(graph.characters.get(edge.source)):
            source_ids.add(edge.source)
        elif edge.source in family_ids and is_lore_source_node(graph.characters.get(edge.target)):
            source_ids.add(edge.target)
    return source_ids


def directly_associated_family_node_ids(graph: CombinedCharacterGraph, node_id: str) -> set[str]:
    family_ids: set[str] = set()
    for associated_id in directly_associated_node_ids(graph, node_id):
        associated_node = graph.characters.get(associated_id)
        if associated_node is not None and associated_node.node_type == "family":
            family_ids.add(associated_id)
    return family_ids


def session_sibling_node_ids(graph: CombinedCharacterGraph, node_id: str) -> set[str]:
    source_ids = {
        edge.source
        for edge in graph.edges
        if edge.target == node_id and is_lore_source_node(graph.characters.get(edge.source))
    }
    source_ids.update(
        edge.target
        for edge in graph.edges
        if edge.source == node_id and is_lore_source_node(graph.characters.get(edge.target))
    )
    if not source_ids:
        return set()
    siblings: set[str] = set()
    for edge in graph.edges:
        if edge.source in source_ids:
            siblings.add(edge.target)
        if edge.target in source_ids:
            siblings.add(edge.source)
    return siblings


def evidence_between_or_from_source(graph: CombinedCharacterGraph, node_id: str, associated_id: str) -> list[str]:
    evidence: list[str] = []
    node = graph.characters.get(node_id)
    associated_node = graph.characters.get(associated_id)
    family_ids = directly_associated_family_node_ids(graph, node_id)
    source_ids = {
        edge.source
        for edge in graph.edges
        if edge.target == node_id and is_lore_source_node(graph.characters.get(edge.source))
    }
    source_ids.update(
        edge.target
        for edge in graph.edges
        if edge.source == node_id and is_lore_source_node(graph.characters.get(edge.target))
    )
    for edge in graph.edges:
        direct_match = {edge.source, edge.target} == {node_id, associated_id}
        session_sibling_match = (
            edge.target == associated_id
            and edge.source in source_ids
            and evidence_mentions_node(edge.evidence, node)
        )
        indirect_family_source_match = (
            is_lore_source_node(associated_node)
            and (
                (edge.source == associated_id and edge.target in family_ids)
                or (edge.target == associated_id and edge.source in family_ids)
            )
        )
        if direct_match:
            for item in edge.evidence:
                if item and item not in evidence:
                    evidence.append(item)
        elif session_sibling_match:
            for item in edge.evidence:
                if item and item not in evidence and evidence_mentions_node([item], node):
                    evidence.append(item)
        elif indirect_family_source_match:
            for item in edge.evidence:
                if item and item not in evidence:
                    evidence.append(item)
    return evidence


def evidence_mentions_node(evidence: list[str], node: CombinedCharacterNode | None) -> bool:
    if node is None:
        return False
    refs = node_name_refs(node.name)
    text = " ".join(evidence)
    return any(re.search(rf"\b{re.escape(ref)}\b", text, re.IGNORECASE) for ref in refs if ref)


def node_name_refs(name: str) -> set[str]:
    refs = {name}
    parts = name.split()
    if parts and parts[0].lower().rstrip(".") not in {"character", "session", "notes", "mr", "mrs", "ms", "mx", "dr"}:
        refs.add(parts[0])
    refs.update(CANONICAL_SESSION_NAME_VARIANTS.get(compact(name), set()))
    return refs


def is_session_notes_node(node: CombinedCharacterNode | None) -> bool:
    if node is None:
        return False
    if node.node_type == "source_document":
        return False
    source_file = node.source_file.replace("\\", "/").lower()
    source_name = source_file.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    return (
        compact(node.name) in {"sessionnotes", "sessionnote"}
        or (
            ("/session_notes/" in source_file or source_file.endswith("/session_notes.md"))
            and compact(node.name) == compact(source_name)
        )
    )


def is_lore_source_node(node: CombinedCharacterNode | None) -> bool:
    return node is not None and (node.node_type == "source_document" or is_session_notes_node(node))


def graph_clarity_metric(graph: CombinedCharacterGraph) -> GraphClarityMetric:
    node_count = len(graph.characters)
    edge_count = len(graph.edges)
    outgoing_counts: dict[str, int] = {}
    for edge in graph.edges:
        outgoing_counts[edge.source] = outgoing_counts.get(edge.source, 0) + 1
    max_outgoing_edges = max(outgoing_counts.values(), default=0)
    possible_directed_edges = node_count * max(node_count - 1, 1)
    edge_density = edge_count / possible_directed_edges if node_count else 0.0
    complexity_penalty = (
        node_count * 1.35
        + edge_count * 1.55
        + max_outgoing_edges * 1.8
        + edge_density * 45
    )
    score = max(0, min(100, round(100 - complexity_penalty)))
    return GraphClarityMetric(
        score=score,
        grade=graph_clarity_grade(score),
        node_count=node_count,
        edge_count=edge_count,
        max_outgoing_edges=max_outgoing_edges,
        edge_density=round(edge_density, 3),
    )


def graph_clarity_grade(score: int) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def graph_clarity_rows(full_graph: CombinedCharacterGraph, focused_graph: CombinedCharacterGraph) -> list[dict[str, str]]:
    return [
        graph_clarity_row("Before Selection", graph_clarity_metric(full_graph)),
        graph_clarity_row("Selected View", graph_clarity_metric(focused_graph)),
    ]


def graph_clarity_row(label: str, metric: GraphClarityMetric) -> dict[str, str]:
    return {
        "View": label,
        "Grade": metric.grade,
        "Score": f"{metric.score}/100",
        "Nodes": str(metric.node_count),
        "Edges": str(metric.edge_count),
        "Max Outgoing": str(metric.max_outgoing_edges),
        "Density": f"{metric.edge_density:.3f}",
    }


def combined_relationship_dot(
    graph: CombinedCharacterGraph,
    focus_node_id: str = "",
    main_character_ids: set[str] | None = None,
    main_place_ids: set[str] | None = None,
    label_font_color: str = "#cbd5e1",
) -> str:
    main_character_keys = {compact(value) for value in main_character_ids or set()}
    main_place_keys = {compact(value) for value in main_place_ids or set()}
    display_characters = graph.characters
    if focus_node_id in display_characters:
        main_character_keys.update({compact(focus_node_id), compact(display_characters[focus_node_id].name)})
    display_edges = [
        edge
        for edge in graph.edges
        if edge.source in display_characters and edge.target in display_characters
    ]
    display_edges = prominent_relationship_edges(display_edges)
    column_layout_requested = bool(main_character_keys or main_place_keys)
    vertical_layout = should_use_vertical_layout(graph) and not column_layout_requested
    rankdir = "TB" if vertical_layout else "LR"
    broad_source = broad_layout_source(
        CombinedCharacterGraph(display_characters, display_edges)
    ) if vertical_layout else ""
    ranksep, nodesep = graph_layout_spacing(
        len(display_characters),
        column_layout_requested=column_layout_requested,
        vertical_layout=vertical_layout,
    )
    lines = [
        "digraph CombinedCharacterRelationships {",
        f"  graph [rankdir={rankdir}, bgcolor=\"transparent\", ranksep={ranksep}, nodesep={nodesep}, splines=\"line\"];",
        "  node [style=\"rounded,filled\", fillcolor=\"#dbeafe\", color=\"#94a3b8\", fontname=\"Inter\", fontcolor=\"#000000\", shape=\"box\"];",
        f"  edge [color=\"#64748b\", fontname=\"Inter\", fontsize=10, fontcolor=\"{escape_dot(label_font_color)}\", labelfontcolor=\"{escape_dot(label_font_color)}\"];",
    ]
    column_groups = graph_column_groups(display_characters, display_edges, main_character_keys, main_place_keys)
    column_by_node = graph_column_by_node(column_groups)
    for character_id, character in display_characters.items():
        fill = (
            "#fde68a"
            if character.node_type == "source_document"
            else "#dcfce7"
            if character.node_type == "place"
            else "#e9d5ff"
            if character.node_type == "group"
            else "#fef3c7"
            if character.node_type == "family"
            else "#dbeafe"
        )
        color = "#ef4444" if character_id == focus_node_id else "#94a3b8"
        penwidth = "2.5" if character_id == focus_node_id else "1"
        shape = (
            "folder"
            if character.node_type == "source_document"
            else "component"
            if character.node_type == "place"
            else "trapezium"
            if character.node_type == "group"
            else "ellipse"
            if character.node_type == "family"
            else "box"
        )
        dimensions = node_dimension_attributes(character.node_type)
        lines.append(
            f'  "{escape_dot(character_id)}" [label="{escape_dot(character.name)}", '
            f'fillcolor="{fill}", color="{color}", penwidth="{penwidth}", shape="{shape}"{dimensions}];'
        )
    lines.extend(graph_column_rank_lines(column_groups))
    for edge in display_edges:
        constraint = edge_constraint_attribute(
            edge,
            column_by_node,
            column_layout_requested,
            vertical_layout,
            broad_source,
        )
        lines.append(edge_dot_statement(edge, display_characters, constraint))
    if vertical_layout and broad_source:
        targets = [
            edge.target
            for edge in display_edges
            if edge.source == broad_source and edge.target in display_characters
        ]
        targets = list(dict.fromkeys(targets))
        if targets:
            lines.append(f'  "{escape_dot(broad_source)}" -> "{escape_dot(targets[0])}" [style=invis, weight=20];')
        for previous, current in zip(targets, targets[1:]):
            lines.append(f'  "{escape_dot(previous)}" -> "{escape_dot(current)}" [style=invis, weight=20];')
    lines.append("}")
    return "\n".join(lines)


def node_dimension_attributes(node_type: str) -> str:
    if node_type == "source_document":
        return ', width=1.65, height=0.7, margin="0.12,0.06"'
    if node_type == "family":
        return ', width=1.9, height=0.8, margin="0.14,0.06"'
    return ""


def graph_layout_spacing(node_count: int, *, column_layout_requested: bool, vertical_layout: bool) -> tuple[str, str]:
    if node_count <= 8:
        return "1.15", "0.4"
    if column_layout_requested:
        return "0.65", "0.35"
    if vertical_layout:
        return "0.6", "0.35"
    return "0.65", "0.35"


def edge_label_attributes(label: str) -> str:
    return f'label="{escape_dot(label)}"'


def edge_dot_statement(
    edge: CombinedRelationshipEdge,
    nodes: dict[str, CombinedCharacterNode],
    constraint: str,
) -> str:
    return (
        f'  "{escape_dot(edge.source)}" -> "{escape_dot(edge.target)}" '
        f'[{edge_label_attributes(edge.relationship_label)}{constraint}];'
    )


def graph_column_groups(
    nodes: dict[str, CombinedCharacterNode],
    edges: list[CombinedRelationshipEdge],
    main_character_keys: set[str],
    main_place_keys: set[str],
) -> dict[str, list[str]]:
    groups = {
        "column_0_family_names": [],
        "column_1_main_characters": [],
        "column_2_secondary_characters": [],
        "column_3_places": [],
    }
    weights = node_mention_weights(edges)
    for node_id, node in nodes.items():
        key = compact(node.name)
        if node.node_type == "family":
            groups["column_0_family_names"].append(node_id)
        elif node.node_type == "group":
            groups["column_0_family_names"].append(node_id)
        elif node.node_type == "source_document":
            groups["column_0_family_names"].append(node_id)
        elif node.node_type == "place" and main_place_keys:
            groups["column_3_places"].append(node_id)
        elif node.node_type == "place":
            groups["column_2_secondary_characters"].append(node_id)
        elif key in main_character_keys or compact(node_id) in main_character_keys:
            groups["column_1_main_characters"].append(node_id)
        else:
            groups["column_2_secondary_characters"].append(node_id)
    for group_name, group_ids in groups.items():
        group_ids.sort(
            key=lambda current_id: (
                graph_column_node_type_rank(group_name, nodes[current_id].node_type),
                0 if compact(nodes[current_id].name) in main_place_keys or compact(current_id) in main_place_keys else 1,
                -weights.get(current_id, 0),
                nodes[current_id].name.lower(),
            )
        )
    return groups


def graph_column_node_type_rank(group_name: str, node_type: str) -> int:
    if group_name == "column_0_family_names":
        return {
            "source_document": 0,
            "family": 1,
            "group": 2,
        }.get(node_type, 3)
    return 0


def graph_column_by_node(column_groups: dict[str, list[str]]) -> dict[str, str]:
    return {
        node_id: group_name
        for group_name, node_ids in column_groups.items()
        for node_id in node_ids
    }


def edge_constraint_attribute(
    edge: CombinedRelationshipEdge,
    column_by_node: dict[str, str],
    column_layout_requested: bool,
    vertical_layout: bool,
    broad_source: str,
) -> str:
    if vertical_layout and edge.source == broad_source:
        return ', constraint="false"'
    if column_layout_requested and column_by_node.get(edge.source) == column_by_node.get(edge.target):
        return ', constraint="false"'
    return ""


def prominent_relationship_edges(edges: list[CombinedRelationshipEdge]) -> list[CombinedRelationshipEdge]:
    grouped: dict[tuple[str, str], list[CombinedRelationshipEdge]] = {}
    first_seen: dict[tuple[str, str], int] = {}
    for index, edge in enumerate(edges):
        key = (edge.source, edge.target)
        grouped.setdefault(key, []).append(edge)
        first_seen.setdefault(key, index)
    collapsed: list[CombinedRelationshipEdge] = []
    for key, group_edges in grouped.items():
        evidence: list[str] = []
        for edge in group_edges:
            for item in edge.evidence:
                if item and item not in evidence:
                    evidence.append(item)
        prominent = sorted(
            group_edges,
            key=lambda edge: (
                -len(edge.evidence),
                relationship_prominence_rank(edge.relationship_type),
                edge.relationship_label.lower(),
            ),
        )[0]
        collapsed.append(
            CombinedRelationshipEdge(
                source=prominent.source,
                target=prominent.target,
                relationship_type=prominent.relationship_type,
                relationship_label=prominent.relationship_label,
                evidence=evidence,
            )
        )
    return sorted(collapsed, key=lambda edge: first_seen[(edge.source, edge.target)])


def node_mention_weights(edges: list[CombinedRelationshipEdge]) -> dict[str, int]:
    weights: dict[str, int] = {}
    for edge in edges:
        weight = max(1, len(edge.evidence))
        weights[edge.source] = weights.get(edge.source, 0) + weight
        weights[edge.target] = weights.get(edge.target, 0) + weight
    return weights


def graph_column_rank_lines(column_groups: dict[str, list[str]]) -> list[str]:
    lines: list[str] = []
    previous_anchor = ""
    for index, (group_name, node_ids) in enumerate(column_groups.items()):
        anchor = f"graph_column_{index}"
        lines.append(f'  "{anchor}" [label="", shape=point, width=0.01, style=invis];')
        if node_ids:
            ranked = "; ".join(f'"{escape_dot(node_id)}"' for node_id in node_ids)
            lines.append(f'  subgraph "cluster_{group_name}" {{ rank=same; style=invis; "{anchor}"; {ranked}; }}')
        else:
            lines.append(f'  subgraph "cluster_{group_name}" {{ rank=same; style=invis; "{anchor}"; }}')
        for previous_node, current_node in zip(node_ids, node_ids[1:]):
            lines.append(
                f'  "{escape_dot(previous_node)}" -> "{escape_dot(current_node)}" '
                '[style=invis, weight=50, constraint="false"];'
            )
        if previous_anchor:
            lines.append(f'  "{previous_anchor}" -> "{anchor}" [style=invis, weight=100];')
        previous_anchor = anchor
    return lines


def should_use_vertical_layout(graph: CombinedCharacterGraph) -> bool:
    if len(graph.characters) <= 20:
        return False
    outgoing_counts: dict[str, int] = {}
    for edge in graph.edges:
        outgoing_counts[edge.source] = outgoing_counts.get(edge.source, 0) + 1
    return max(outgoing_counts.values(), default=0) >= 12


def broad_layout_source(graph: CombinedCharacterGraph) -> str:
    outgoing_counts: dict[str, int] = {}
    for edge in graph.edges:
        outgoing_counts[edge.source] = outgoing_counts.get(edge.source, 0) + 1
    if not outgoing_counts:
        return ""
    return max(outgoing_counts, key=outgoing_counts.get)


def compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def display_name(value: str) -> str:
    return value.replace("_", " ")


def compact_evidence(values: list[str]) -> str:
    return " ".join(clean_evidence_text(value) for value in values if value.strip())


def clean_evidence_text(value: str) -> str:
    return re.sub(r"^\s*(?:#{1,6}|[-*+]|[0-9]+[.)])\s+", "", " ".join(value.split()))


def escape_dot(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
