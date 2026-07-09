from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from .embeddings import HashingEmbedder, cosine_similarity
from .schema import AttributeNode, CharacterGraph, CharacterNode, PlaceNode, RelationshipEdge


@dataclass(frozen=True)
class RetrievedCharacterContext:
    node_id: str
    node: CharacterNode | AttributeNode | PlaceNode
    display_name: str
    relationships: list[RelationshipEdge]
    score: float
    matched_by: list[str]


def retrieve_relevant_context(
    graph: CharacterGraph,
    message: str,
    limit: int = 3,
    min_score: float = 0.18,
) -> list[RetrievedCharacterContext]:
    embedder = HashingEmbedder()
    message_vector = embedder.embed(message)
    message_lower = message.lower()
    results: list[RetrievedCharacterContext] = []

    for character_id, character in graph.characters.items():
        if character_id == graph.primary_character.id:
            continue
        result = score_node(
            graph=graph,
            node_id=character_id,
            node=character,
            labels=[character.name, *character.aliases],
            display_name=character.name,
            message_lower=message_lower,
            message_vector=message_vector,
            min_score=min_score,
        )
        if result:
            results.append(result)

    for attribute_id, attribute in graph.attributes.items():
        result = score_node(
            graph=graph,
            node_id=attribute_id,
            node=attribute,
            labels=[attribute.value, attribute.attribute_type, *attribute.aliases],
            display_name=attribute.value,
            message_lower=message_lower,
            message_vector=message_vector,
            min_score=min_score,
        )
        if result:
            results.append(result)

    for place_id, place in graph.places.items():
        result = score_node(
            graph=graph,
            node_id=place_id,
            node=place,
            labels=[place.name, place.place_type, *place.aliases],
            display_name=place.name,
            message_lower=message_lower,
            message_vector=message_vector,
            min_score=min_score,
        )
        if result:
            results.append(result)

    return sorted(results, key=lambda result: result.score, reverse=True)[:limit]


def score_node(
    graph: CharacterGraph,
    node_id: str,
    node: CharacterNode | AttributeNode | PlaceNode,
    labels: list[str],
    display_name: str,
    message_lower: str,
    message_vector: list[float],
    min_score: float,
) -> RetrievedCharacterContext | None:
    score = 0.0
    matched_by: list[str] = []
    for label in labels:
        label_lower = label.lower()
        if label_lower and label_lower in message_lower:
            score += 1.0
            matched_by.append(label)
        else:
            ratio = SequenceMatcher(None, label_lower, message_lower).ratio()
            if ratio >= 0.72:
                score += ratio
                matched_by.append(f"fuzzy:{label}")
    embedding = graph.embeddings.get(node_id)
    if embedding:
        semantic_score = max(0.0, cosine_similarity(message_vector, embedding.vector))
        score += semantic_score
        if semantic_score >= min_score:
            matched_by.append("semantic")
    if score < min_score:
        return None
    return RetrievedCharacterContext(
        node_id=node_id,
        node=node,
        display_name=display_name,
        relationships=relationships_for(graph, node_id),
        score=score,
        matched_by=matched_by,
    )


def relationships_for(graph: CharacterGraph, node_id: str) -> list[RelationshipEdge]:
    return [
        relationship
        for relationship in graph.relationships
        if relationship.source == node_id or relationship.target == node_id
    ]
