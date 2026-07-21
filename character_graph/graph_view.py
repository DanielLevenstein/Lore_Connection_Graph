from __future__ import annotations

import re

from .schema import CharacterGraph


EVIDENCE_MAX_LENGTH = 240


def relationship_rows(graph: CharacterGraph) -> list[dict[str, str | float]]:
    rows: list[dict[str, str | float]] = []
    for relationship in graph.relationships:
        if relationship.target in graph.attributes or relationship.target in graph.places:
            continue
        source = graph.characters.get(relationship.source)
        rows.append(
            {
                "Character": source.name if source else node_label(graph, relationship.source),
                "Relationship": relationship.relationship_label,
                "Value": node_label(graph, relationship.target),
            }
        )
    return rows


def visible_relationship_count(graph: CharacterGraph) -> int:
    return sum(1 for relationship in graph.relationships if relationship.target in graph.characters)


def attribute_rows(graph: CharacterGraph) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for attribute in graph.attributes.values():
        rows.append(
            {
                "Value": display_value(attribute.value),
                "Attribute": attribute.attribute_type,
                "Aliases": ", ".join(attribute.aliases),
                "Summary": attribute.summary,
            }
        )
    return rows


def place_rows(graph: CharacterGraph) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for place in graph.places.values():
        rows.append(
            {
                "Value": display_value(place.name),
                "Attribute": place.place_type.title(),
                "Aliases": ", ".join(place.aliases),
                "Summary": place.summary,
            }
        )
    return rows


def evidence_rows(graph: CharacterGraph) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for relationship in graph.relationships:
        if relationship.target in graph.attributes or relationship.target in graph.places:
            continue
        rows.append(
            {
                "Table": "Relationships",
                "Item": relationship.relationship_label,
                "Value": display_value(node_label(graph, relationship.target)),
                "Evidence": limit_evidence(" ".join(relationship.evidence)),
            }
        )
    for attribute in graph.attributes.values():
        rows.append(
            {
                "Table": "Attributes",
                "Item": attribute.attribute_type,
                "Value": display_value(attribute.value),
                "Evidence": limit_evidence(" ".join(attribute.source_spans)),
            }
        )
    for place in graph.places.values():
        rows.append(
            {
                "Table": "Places",
                "Item": place.place_type.title(),
                "Value": display_value(place.name),
                "Evidence": limit_evidence(" ".join(place.source_spans)),
            }
        )
    return rows


def limit_evidence(value: str, max_length: int = EVIDENCE_MAX_LENGTH) -> str:
    cleaned = re.sub(r"^\s*(?:[-*+]|[0-9]+[.)])\s+", "", " ".join(value.split()))
    if len(cleaned) <= max_length:
        return cleaned
    sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", cleaned) if sentence.strip()]
    if sentences and len(sentences[0]) <= max_length:
        return sentences[0]
    return cleaned[: max_length - 3].rstrip() + "..."


def display_value(value: str) -> str:
    return " ".join(value.replace("_", " ").split())


def relationship_dot(graph: CharacterGraph) -> str:
    lines = [
        "digraph CharacterRelationships {",
        "  graph [rankdir=LR, bgcolor=\"transparent\"];",
        "  node [style=\"filled\", fillcolor=\"#f8fafc\", color=\"#94a3b8\", fontname=\"Inter\"];",
        "  edge [color=\"#64748b\", fontname=\"Inter\", fontsize=10];",
    ]
    for character_id, character in graph.characters.items():
        lines.append(
            f'  "{escape_dot(character_id)}" [label="{escape_dot(character.name)}", '
            'fillcolor="#dbeafe", shape="box", style="rounded,filled"];'
        )
    for attribute_id, attribute in graph.attributes.items():
        lines.append(
            f'  "{escape_dot(attribute_id)}" [label="{escape_dot(attribute.value)}", '
            'fillcolor="#f8fafc", shape="ellipse", style="filled"];'
        )
    for place_id, place in graph.places.items():
        lines.append(
            f'  "{escape_dot(place_id)}" [label="{escape_dot(place.name)}", '
            'fillcolor="#dcfce7", shape="component", style="filled"];'
        )
    for relationship in graph.relationships:
        label = relationship.relationship_label
        lines.append(
            f'  "{escape_dot(relationship.source)}" -> "{escape_dot(relationship.target)}" '
            f'[label="{escape_dot(label)}", color="#64748b"];'
        )
    lines.append("}")
    return "\n".join(lines)


def escape_dot(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def node_label(graph: CharacterGraph, node_id: str) -> str:
    if node_id in graph.characters:
        return graph.characters[node_id].name
    if node_id in graph.attributes:
        return graph.attributes[node_id].value
    if node_id in graph.places:
        return graph.places[node_id].name
    return node_id
