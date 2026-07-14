from __future__ import annotations

from .schema import SCHEMA_VERSION, CharacterGraph


def validate_graph(graph: CharacterGraph, expected_source_hash: str | None = None) -> list[str]:
    warnings: list[str] = []
    graph_node_ids = set(graph.characters) | set(graph.attributes) | set(graph.places)
    if graph.schema_version != SCHEMA_VERSION:
        warnings.append(f"Schema version mismatch: expected {SCHEMA_VERSION}, found {graph.schema_version}.")
    if not graph.primary_character.source_file.strip():
        warnings.append("Primary character source file is missing.")
    if graph.primary_character.id not in graph.characters:
        warnings.append(f"Primary character `{graph.primary_character.id}` is missing from characters.")
    for character_id, character in graph.characters.items():
        if not character.summary.strip():
            warnings.append(f"Character `{character_id}` has no summary.")
        if character_id not in graph.embeddings:
            warnings.append(f"Character `{character_id}` has no embedding record.")
    for attribute_id, attribute in graph.attributes.items():
        if not attribute.summary.strip():
            warnings.append(f"Attribute `{attribute_id}` has no summary.")
        if attribute_id not in graph.embeddings:
            warnings.append(f"Attribute `{attribute_id}` has no embedding record.")
    for place_id, place in graph.places.items():
        if not place.summary.strip():
            warnings.append(f"Place `{place_id}` has no summary.")
        if place_id not in graph.embeddings:
            warnings.append(f"Place `{place_id}` has no embedding record.")
    for relationship in graph.relationships:
        if relationship.source not in graph_node_ids:
            warnings.append(f"Relationship source `{relationship.source}` is missing from graph nodes.")
        if relationship.target not in graph_node_ids:
            warnings.append(f"Relationship target `{relationship.target}` is missing from graph nodes.")
        if not any(item.strip() for item in relationship.evidence):
            warnings.append(f"Relationship `{relationship.source}` -> `{relationship.target}` has no evidence.")
    for embedding_id, embedding in graph.embeddings.items():
        if embedding_id not in graph_node_ids:
            warnings.append(f"Embedding `{embedding_id}` does not match a graph node.")
        if embedding.node_id != embedding_id:
            warnings.append(f"Embedding `{embedding_id}` has mismatched node id `{embedding.node_id}`.")
        if not embedding.embedding_text.strip():
            warnings.append(f"Embedding `{embedding_id}` has no source text.")
        if not embedding.vector:
            warnings.append(f"Embedding `{embedding_id}` has no vector.")
    if expected_source_hash and graph.metadata and graph.metadata.source_hash != expected_source_hash:
        warnings.append("Source file changed since the graph was generated.")
    return warnings
