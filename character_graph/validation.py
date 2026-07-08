from __future__ import annotations

from .schema import SCHEMA_VERSION, CharacterGraph


def validate_graph(graph: CharacterGraph, expected_source_hash: str | None = None) -> list[str]:
    warnings: list[str] = []
    if graph.schema_version != SCHEMA_VERSION:
        warnings.append(f"Schema version mismatch: expected {SCHEMA_VERSION}, found {graph.schema_version}.")
    if graph.primary_character.id not in graph.characters:
        warnings.append(f"Primary character `{graph.primary_character.id}` is missing from characters.")
    for character_id, character in graph.characters.items():
        if not character.summary.strip():
            warnings.append(f"Character `{character_id}` has no summary.")
    for attribute_id, attribute in graph.attributes.items():
        if not attribute.summary.strip():
            warnings.append(f"Attribute `{attribute_id}` has no summary.")
    for relationship in graph.relationships:
        if relationship.source not in graph.characters and relationship.source not in graph.attributes:
            warnings.append(f"Relationship source `{relationship.source}` is missing from graph nodes.")
        if relationship.target not in graph.characters and relationship.target not in graph.attributes:
            warnings.append(f"Relationship target `{relationship.target}` is missing from graph nodes.")
        if not relationship.evidence:
            warnings.append(f"Relationship `{relationship.source}` -> `{relationship.target}` has no evidence.")
    if expected_source_hash and graph.metadata and graph.metadata.source_hash != expected_source_hash:
        warnings.append("Source file changed since the graph was generated.")
    return warnings
