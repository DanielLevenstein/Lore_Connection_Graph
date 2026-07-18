from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SCHEMA_VERSION = "0.3.0"


@dataclass
class PrimaryCharacterRef:
    id: str
    name: str
    source_file: str


@dataclass
class Alignment:
    moral_alignment: str = "unknown"
    faction_alignment: list[str] = field(default_factory=list)
    loyalty_targets: list[str] = field(default_factory=list)
    opposition_targets: list[str] = field(default_factory=list)


@dataclass
class CharacterNode:
    name: str
    aliases: list[str] = field(default_factory=list)
    role: str = "unknown"
    summary: str = ""
    motivations: list[str] = field(default_factory=list)
    traits: list[str] = field(default_factory=list)
    alignment: Alignment = field(default_factory=Alignment)
    source_spans: list[str] = field(default_factory=list)


@dataclass
class AttributeNode:
    value: str
    attribute_type: str
    aliases: list[str] = field(default_factory=list)
    summary: str = ""
    source_spans: list[str] = field(default_factory=list)


@dataclass
class PlaceNode:
    name: str
    place_type: str = "place"
    aliases: list[str] = field(default_factory=list)
    summary: str = ""
    source_spans: list[str] = field(default_factory=list)


@dataclass
class RelationshipEdge:
    source: str
    target: str
    relationship_type: str = "unknown"
    relationship_label: str = "unknown"
    sentiment: str = "unknown"
    trust_level: float = 0.5
    conflict_level: float = 0.0
    emotional_weight: float = 0.4
    evidence: list[str] = field(default_factory=list)


@dataclass
class EmbeddingRecord:
    node_id: str
    embedding_text: str
    embedding_ref: str
    vector: list[float] = field(default_factory=list)


@dataclass
class GraphMetadata:
    backup_date: str
    snapshot_date: str
    source_hash: str


@dataclass
class CharacterGraph:
    schema_version: str
    primary_character: PrimaryCharacterRef
    characters: dict[str, CharacterNode] = field(default_factory=dict)
    attributes: dict[str, AttributeNode] = field(default_factory=dict)
    places: dict[str, PlaceNode] = field(default_factory=dict)
    relationships: list[RelationshipEdge] = field(default_factory=list)
    embeddings: dict[str, EmbeddingRecord] = field(default_factory=dict)
    metadata: GraphMetadata | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CharacterGraph:
        primary = PrimaryCharacterRef(**payload["primary_character"])
        characters = {
            character_id: _character_node_from_dict(node)
            for character_id, node in payload.get("characters", {}).items()
        }
        attributes = {
            attribute_id: _attribute_node_from_dict(node)
            for attribute_id, node in payload.get("attributes", {}).items()
        }
        places = {
            place_id: _place_node_from_dict(node)
            for place_id, node in payload.get("places", {}).items()
        }
        payload_schema_version = payload.get("schema_version", SCHEMA_VERSION)
        if not attributes and payload_schema_version == "0.1.0":
            characters, attributes = _migrate_legacy_attribute_nodes(primary.id, characters)
        relationships = [RelationshipEdge(**edge) for edge in payload.get("relationships", [])]
        embeddings = {
            key: _embedding_record_from_dict(record)
            for key, record in payload.get("embeddings", {}).items()
        }
        metadata_payload = payload.get("metadata")
        metadata = GraphMetadata(**metadata_payload) if isinstance(metadata_payload, dict) else None
        return cls(
            schema_version=payload_schema_version,
            primary_character=primary,
            characters=characters,
            attributes=attributes,
            places=places,
            relationships=relationships,
            embeddings=embeddings,
            metadata=metadata,
        )


def _character_node_from_dict(payload: dict[str, Any]) -> CharacterNode:
    alignment_payload = payload.get("alignment")
    alignment = Alignment(**alignment_payload) if isinstance(alignment_payload, dict) else Alignment()
    return CharacterNode(
        name=payload.get("name", ""),
        aliases=list(payload.get("aliases", [])),
        role=payload.get("role", "unknown"),
        summary=payload.get("summary", ""),
        motivations=list(payload.get("motivations", [])),
        traits=list(payload.get("traits", [])),
        alignment=alignment,
        source_spans=list(payload.get("source_spans", [])),
    )


def _attribute_node_from_dict(payload: dict[str, Any]) -> AttributeNode:
    return AttributeNode(
        value=payload.get("value", payload.get("name", "")),
        attribute_type=payload.get("attribute_type", payload.get("role", "unknown")),
        aliases=list(payload.get("aliases", [])),
        summary=payload.get("summary", ""),
        source_spans=list(payload.get("source_spans", [])),
    )


def _place_node_from_dict(payload: dict[str, Any]) -> PlaceNode:
    return PlaceNode(
        name=payload.get("name", payload.get("value", "")),
        place_type=payload.get("place_type", payload.get("role", "place")),
        aliases=list(payload.get("aliases", [])),
        summary=payload.get("summary", ""),
        source_spans=list(payload.get("source_spans", [])),
    )


def _embedding_record_from_dict(payload: dict[str, Any]) -> EmbeddingRecord:
    return EmbeddingRecord(
        node_id=payload.get("node_id", payload.get("character_id", "")),
        embedding_text=payload.get("embedding_text", ""),
        embedding_ref=payload.get("embedding_ref", ""),
        vector=list(payload.get("vector", [])),
    )


def _migrate_legacy_attribute_nodes(
    primary_id: str,
    characters: dict[str, CharacterNode],
) -> tuple[dict[str, CharacterNode], dict[str, AttributeNode]]:
    migrated_characters: dict[str, CharacterNode] = {}
    migrated_attributes: dict[str, AttributeNode] = {}
    for node_id, node in characters.items():
        if node_id == primary_id:
            migrated_characters[node_id] = node
        else:
            migrated_attributes[node_id] = AttributeNode(
                value=node.name,
                attribute_type=node.role,
                aliases=node.aliases,
                summary=node.summary,
                source_spans=node.source_spans,
            )
    return migrated_characters, migrated_attributes
