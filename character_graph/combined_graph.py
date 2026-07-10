from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from .schema import CharacterGraph


PRESERVED_RELATIONSHIP_TYPES = {
    "ally",
    "enemy",
    "lover",
    "rival",
    "betrayer",
    "client",
    "mentor",
}


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


def build_combined_character_graph(
    graphs: list[CharacterGraph],
    place_sources: list[tuple[str, str, str]] | None = None,
    lore_relationships: list[dict[str, str]] | None = None,
) -> CombinedCharacterGraph:
    combined = CombinedCharacterGraph()
    for graph in graphs:
        combined.characters[graph.primary_character.id] = CombinedCharacterNode(
            id=graph.primary_character.id,
            name=display_name(graph.primary_character.name),
            source_file=graph.primary_character.source_file,
            node_type="character",
        )
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
                node_type=relationship.get("source_type", "place"),
            ),
        )
        combined.characters.setdefault(
            target_id,
            CombinedCharacterNode(
                id=target_id,
                name=display_name(relationship.get("target_name", target_id)),
                source_file=relationship.get("target_file", relationship.get("source_file", "")),
                node_type=relationship.get("target_type", "character"),
            ),
        )
    by_key: dict[tuple[str, str, str], CombinedRelationshipEdge] = {}

    for graph in graphs:
        source_id = graph.primary_character.id
        for relationship in graph.relationships:
            if relationship.target in graph.attributes:
                continue
            target_node = graph.characters.get(relationship.target) or graph.places.get(relationship.target)
            if target_node is None:
                continue
            matched_primary_id = match_primary_character(
                target_node.name,
                relationship.evidence,
                primary_character_nodes(combined.characters),
                source_id,
            ) or relationship.target
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
        if not source_id or not target_id:
            continue
        relationship_type = one_word_relationship(relationship.get("relationship", "reference"))
        relationship_label = relationship_type.title()
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

    return combined


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
    if len(parts) > 1:
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
        return relationship_type, relationship_type.replace("_", " ").title()
    if relationship_type == "place":
        return "place", "Place"
    return "reference", "Referenced"


def one_word_relationship(value: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", value.lower())
    return words[0] if words else "reference"


def combined_relationship_rows(graph: CombinedCharacterGraph) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for edge in graph.edges:
        source = graph.characters.get(edge.source)
        target = graph.characters.get(edge.target)
        rows.append(
            {
                "Character": source.name if source else edge.source,
                "Character Type": source.node_type.title() if source else "",
                "Relationship": edge.relationship_label,
                "Connection": target.name if target else edge.target,
                "Connection Type": target.node_type.title() if target else "",
                "Evidence": " ".join(edge.evidence),
            }
        )
    return rows


def combined_relationship_dot(graph: CombinedCharacterGraph) -> str:
    lines = [
        "digraph CombinedCharacterRelationships {",
        "  graph [rankdir=LR, bgcolor=\"transparent\"];",
        "  node [style=\"rounded,filled\", fillcolor=\"#dbeafe\", color=\"#94a3b8\", fontname=\"Inter\", shape=\"box\"];",
        "  edge [color=\"#64748b\", fontname=\"Inter\", fontsize=10];",
    ]
    for character_id, character in graph.characters.items():
        fill = "#dcfce7" if character.node_type == "place" else "#dbeafe"
        shape = "component" if character.node_type == "place" else "box"
        lines.append(
            f'  "{escape_dot(character_id)}" [label="{escape_dot(character.name)}", '
            f'fillcolor="{fill}", shape="{shape}"];'
        )
    for edge in graph.edges:
        lines.append(
            f'  "{escape_dot(edge.source)}" -> "{escape_dot(edge.target)}" '
            f'[label="{escape_dot(edge.relationship_label)}"];'
        )
    lines.append("}")
    return "\n".join(lines)


def compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def display_name(value: str) -> str:
    return value.replace("_", " ")


def escape_dot(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
