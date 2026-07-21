from __future__ import annotations

import re
from datetime import datetime

from .embeddings import build_embedding_record
from .ingest import BackstoryDocument
from .schema import (
    SCHEMA_VERSION,
    Alignment,
    AttributeNode,
    CharacterGraph,
    CharacterNode,
    GraphMetadata,
    PlaceNode,
    PrimaryCharacterRef,
    RelationshipEdge,
)


NAME_PATTERN = re.compile(r"\b([A-Z][a-z]+(?:[ \t]+(?:the[ \t]+)?[A-Z][a-z]+){0,3})\b")
HEADING_PATTERN = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
SENTENCE_PATTERN = re.compile(r"[^.!?\n]+[.!?]?")
HONORIFIC_WORDS = {"Mr", "Mrs", "Ms", "Mx", "Dr", "Miss"}
UNKNOWN_VALUES = {"", "unknown", "none", "n/a", "na", "unspecified", "not specified", "tbd"}
NON_NAME_WORDS = {
    "A",
    "An",
    "And",
    "As",
    "At",
    "But",
    "By",
    "For",
    "From",
    "Haunted",
    "He",
    "Her",
    "His",
    "I",
    "In",
    "It",
    "Its",
    "Most",
    "No",
    "On",
    "Or",
    "One",
    "She",
    "That",
    "The",
    "Their",
    "They",
    "This",
    "Those",
    "When",
    "Where",
    "While",
    "With",
}
PLACE_SUFFIXES = {
    "Academy",
    "Bastion",
    "Cavern",
    "City",
    "College",
    "Coast",
    "Court",
    "Fortress",
    "Forest",
    "Guild",
    "Hall",
    "Halls",
    "Harbor",
    "Keep",
    "Kingdom",
    "Library",
    "Mage College",
    "Monastery",
    "Order",
    "School",
    "Sea",
    "Shore",
    "Shores",
    "Temple",
    "Tower",
    "Tavern",
    "University",
    "Village",
}
GENERIC_PLACE_NAMES = {suffix.lower() for suffix in PLACE_SUFFIXES}
MOTIVATION_PATTERNS = [
    re.compile(r"\b(?:wants|seeks|hopes|needs|tries|trying|adventures)\s+to\s+([^.!?;]+)", re.IGNORECASE),
    re.compile(r"\b(?:goal|motivation)\s+(?:is|was)\s+to\s+([^.!?;]+)", re.IGNORECASE),
]
RELATIONSHIP_RULES = [
    ("betrayer", "Betrayer", "hostile", ("betray", "betrayed", "betraying")),
    ("former_mentor", "Former mentor", "complicated", ("former mentor", "trained", "teacher", "mentor")),
    ("family", "Family", "positive", ("sister", "brother", "mother", "father", "parent", "child", "family")),
    ("client", "Client", "positive", ("client", "customer", "patron", "regular")),
    ("rival", "Rivals", "hostile", ("rival", "competitor")),
    ("enemy", "Enemy", "hostile", ("enemy", "foe", "hates", "opposes", "against")),
    ("ally", "Ally", "positive", ("ally", "companion", "friend", "trusted")),
    ("lover", "Lover", "positive", ("lover", "beloved", "romance", "romantic")),
]

TRAIT_WORDS = {
    "careful",
    "guarded",
    "strategic",
    "resentful",
    "loyal",
    "wary",
    "practical",
    "ambitious",
    "patient",
    "reckless",
    "kind",
    "cruel",
    "brave",
    "fearful",
    "cautious",
    "curious",
}
GENERATED_EVIDENCE_MAX_LENGTH = 240


def extract_character_graph(
    document: BackstoryDocument,
    primary_name: str | None = None,
) -> CharacterGraph:
    stats = extract_character_stats(document.raw_text)
    stats = {**extract_character_details(document.raw_text), **stats}
    primary_name = primary_name or infer_primary_name(document.raw_text, document.character_id, stats)
    primary_id = slugify(primary_name)
    now = datetime.now().isoformat(timespec="seconds")
    sentences = split_sentences(document.raw_text)
    connection_rows = character_connection_rows(document.raw_text)
    place_mentions = find_place_mentions(document.raw_text)
    mentioned_names = find_mentioned_names(document.raw_text, primary_name, stats)

    characters: dict[str, CharacterNode] = {
        primary_id: CharacterNode(
            name=primary_name,
            aliases=[],
            role="primary character",
            summary=extract_primary_summary(document.raw_text, primary_name),
            motivations=extract_motivations(document.raw_text),
            traits=extract_traits(document.raw_text),
            alignment=extract_alignment(document.raw_text),
            source_spans=[span for span in sentences if primary_name.split()[0] in span][:5],
        )
    }
    relationships: list[RelationshipEdge] = []
    attributes: dict[str, AttributeNode] = {}
    places: dict[str, PlaceNode] = {}

    for attribute_type, label, value, evidence in attribute_connections(primary_name, stats, document.raw_text):
        node_id = unique_node_id(attributes, slugify(f"{attribute_type}_{value}"))
        attributes[node_id] = AttributeNode(
            value=value,
            attribute_type=label,
            aliases=[],
            summary=build_metadata_summary(primary_name, label, value, evidence),
            source_spans=[evidence],
        )
        relationships.append(
            RelationshipEdge(
                source=primary_id,
                target=node_id,
                relationship_type=attribute_type,
                relationship_label=label,
                sentiment="metadata",
                trust_level=1.0,
                conflict_level=0.0,
                emotional_weight=0.3,
                evidence=[evidence],
            )
        )
    for place_name, aliases, evidence in place_mentions:
        place_id = unique_place_id(places, slugify(place_name))
        places[place_id] = PlaceNode(
            name=place_name,
            place_type=infer_place_type(place_name),
            aliases=aliases,
            summary=build_place_summary(primary_name, place_name, evidence),
            source_spans=evidence,
        )
        relationships.append(
            RelationshipEdge(
                source=primary_id,
                target=place_id,
                relationship_type="place",
                relationship_label="Place",
                sentiment="setting",
                trust_level=0.8,
                conflict_level=0.0,
                emotional_weight=0.4,
                evidence=evidence,
            )
        )
    for relationship_type, label, value, evidence in character_relationships(primary_name, stats, document.raw_text):
        node_id = unique_character_id(characters, slugify(value))
        if node_id == primary_id:
            continue
        characters[node_id] = CharacterNode(
            name=value,
            aliases=[],
            role=label.lower(),
            summary=f"{value} is connected to {primary_name} as {label.lower()}. Evidence: {evidence}",
            source_spans=[evidence],
        )
        relationships.append(
            RelationshipEdge(
                source=primary_id,
                target=node_id,
                relationship_type=relationship_type,
                relationship_label=label,
                sentiment=relationship_type,
                trust_level=0.8,
                conflict_level=0.7 if relationship_type == "enemy" else 0.0,
                emotional_weight=0.7,
                evidence=[evidence],
            )
        )
    for connection in connection_rows:
        connection_kind = (connection.get("table") or connection.get("source") or "").lower()
        relationship_label = connection.get("relationship") or connection.get("item") or "Referenced"
        relationship_type = slugify(relationship_label) or "reference"
        value = connection.get("name") or connection.get("value") or connection.get("connection") or ""
        if relationship_type == "family" and value.lower() in {"mother", "father", "parent"}:
            value = f"{primary_name}'s {value}"
        evidence = limit_generated_evidence(
            connection.get("evidence") or f"{value} is listed in the Character Connections table."
        )
        if not value:
            continue
        if connection_kind == "attributes":
            node_id = unique_node_id(attributes, slugify(f"{relationship_type}_{value}"))
            attributes[node_id] = AttributeNode(
                value=value,
                attribute_type=relationship_label,
                aliases=[],
                summary=build_metadata_summary(primary_name, relationship_label, value, evidence),
                source_spans=[evidence],
            )
            target_id = node_id
        elif connection_kind == "places" or connection.get("source", "").lower() == "place":
            node_id = unique_place_id(places, slugify(value))
            places[node_id] = PlaceNode(
                name=value,
                place_type=relationship_label.lower(),
                aliases=[],
                summary=build_place_summary(primary_name, value, [evidence]),
                source_spans=[evidence],
            )
            target_id = node_id
            relationship_type = "place"
            relationship_label = relationship_label if relationship_label.lower() != "place" else "Place"
        else:
            node_id = unique_character_id(characters, slugify(value))
            if node_id == primary_id:
                continue
            characters.setdefault(
                node_id,
                CharacterNode(
                    name=value,
                    aliases=[],
                    role=relationship_label.lower(),
                    summary=f"{value} is listed in {primary_name}'s Character Connections as {relationship_label.lower()}.",
                    source_spans=[evidence],
                ),
            )
            target_id = node_id
        relationships.append(
            RelationshipEdge(
                source=primary_id,
                target=target_id,
                relationship_type=relationship_type,
                relationship_label=relationship_label,
                sentiment=relationship_type,
                trust_level=0.8,
                conflict_level=0.7 if relationship_type == "enemy" else 0.0,
                emotional_weight=0.7,
                evidence=[evidence],
            )
        )
    for name in mentioned_names:
        if is_known_place_reference(name, places):
            continue
        character_id = slugify(name)
        if character_id == primary_id:
            continue
        evidence = evidence_for_name(sentences, name)
        relationship = infer_relationship(primary_id, character_id, name, evidence)
        if relationship is None:
            continue
        characters.setdefault(
            character_id,
            CharacterNode(
                name=name,
                aliases=[],
                role=relationship.relationship_label.lower(),
                summary=build_related_summary(name, primary_name, relationship, evidence),
                motivations=[],
                traits=extract_traits(" ".join(evidence)),
                alignment=Alignment(),
                source_spans=evidence,
            ),
        )
        relationships.append(relationship)

    graph = CharacterGraph(
        schema_version=SCHEMA_VERSION,
        primary_character=PrimaryCharacterRef(
            id=primary_id,
            name=primary_name,
            source_file=document.source_file,
        ),
        characters=characters,
        attributes=attributes,
        places=places,
        relationships=dedupe_relationships(relationships),
        metadata=GraphMetadata(
            backup_date=now,
            snapshot_date=now,
            source_hash=document.source_hash,
        ),
    )
    for character_id, node in graph.characters.items():
        embedding_text = " ".join(
            part for part in [node.name, " ".join(node.aliases), node.role, node.summary, " ".join(node.source_spans)] if part
        )
        graph.embeddings[character_id] = build_embedding_record(character_id, embedding_text)
    for attribute_id, node in graph.attributes.items():
        embedding_text = " ".join(
            part
            for part in [node.value, " ".join(node.aliases), node.attribute_type, node.summary, " ".join(node.source_spans)]
            if part
        )
        graph.embeddings[attribute_id] = build_embedding_record(attribute_id, embedding_text)
    for place_id, node in graph.places.items():
        embedding_text = " ".join(
            part for part in [node.name, " ".join(node.aliases), node.place_type, node.summary, " ".join(node.source_spans)] if part
        )
        graph.embeddings[place_id] = build_embedding_record(place_id, embedding_text)
    return graph


def extract_character_stats(text: str) -> dict[str, str]:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        headers = parse_table_row(line)
        normalized_headers = [normalize_stat_key(header) for header in headers]
        if not required_stats_present(normalized_headers):
            continue
        for row in lines[index + 1 :]:
            values = parse_table_row(row)
            if not values:
                continue
            if all(set(value) <= {"-"} for value in values if value):
                continue
            padded_values = values + [""] * max(0, len(headers) - len(values))
            return {
                normalize_stat_key(header): clean_table_cell(value)
                for header, value in zip(headers, padded_values)
            }
    return {}


def extract_character_details(text: str) -> dict[str, str]:
    details = character_details_section(text)
    if not details:
        return {}
    values: dict[str, list[str]] = {}
    values.update(parse_details_table(details))
    current_key = ""
    current_values: list[str] = []
    for line in details.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("|"):
            continue
        if stripped.startswith("-") and current_key:
            current_values.append(stripped.lstrip("-").strip())
            continue
        if current_key:
            values[current_key] = current_values
            current_key = ""
            current_values = []
        if ":" not in stripped:
            continue
        label, value = stripped.split(":", 1)
        key = normalize_detail_key(label)
        if not key:
            continue
        if value.strip():
            values[key] = [value.strip()]
        else:
            current_key = key
            current_values = []
    if current_key:
        values[current_key] = current_values
    return {key: "; ".join(items) for key, items in values.items() if items}


def character_details_section(text: str) -> str:
    match = re.search(r"^###\s+Character Details\s*$", text, re.IGNORECASE | re.MULTILINE)
    if not match:
        return ""
    next_heading = re.search(r"^#{1,3}\s+", text[match.end() :], re.MULTILINE)
    end = match.end() + next_heading.start() if next_heading else len(text)
    return text[match.end() : end].strip()


def parse_details_table(details: str) -> dict[str, list[str]]:
    rows = [parse_table_row(line) for line in details.splitlines()]
    rows = [row for row in rows if row]
    if len(rows) < 3:
        return {}
    headers = [compact_key(header) for header in rows[0]]
    if "field" not in headers or "description" not in headers:
        return {}
    field_index = headers.index("field")
    description_index = headers.index("description")
    values: dict[str, list[str]] = {}
    for row in rows[1:]:
        if len(row) <= max(field_index, description_index):
            continue
        if all(set(cell) <= {"-"} for cell in row):
            continue
        key = normalize_detail_key(row[field_index])
        description = row[description_index].strip()
        if key and description:
            values.setdefault(key, []).append(description)
    return values


def character_connection_rows(text: str) -> list[dict[str, str]]:
    section = markdown_section(text, "Character Connections")
    if not section:
        return []
    rows = [parse_table_row(line) for line in section.splitlines()]
    rows = [row for row in rows if row]
    if len(rows) < 3:
        return []
    headers = [normalize_connection_header(header) for header in rows[0]]
    values: list[dict[str, str]] = []
    for row in rows[1:]:
        if all(set(cell) <= {"-"} for cell in row):
            continue
        item = {
            header: value.strip()
            for header, value in zip(headers, row)
            if header and value.strip()
        }
        if item:
            values.append(item)
    return values

def markdown_section(text: str, heading: str) -> str:
    pattern = re.compile(rf"^#{{2,3}}\s+{re.escape(heading)}\s*$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    next_heading = re.search(r"^#{1,3}\s+", text[match.end() :], re.MULTILINE)
    end = match.end() + next_heading.start() if next_heading else len(text)
    return text[match.end() : end].strip()


def normalize_connection_header(value: str) -> str:
    key = compact_key(value)
    aliases = {
        "connection": "name",
        "relationship": "relationship",
        "item": "item",
        "name": "name",
        "source": "source",
        "table": "table",
        "value": "value",
        "evidence": "evidence",
    }
    return aliases.get(key, key)


def normalize_detail_key(value: str) -> str:
    key = compact_key(value)
    aliases = {
        "ally": "alliances",
        "alliance": "alliances",
        "alliances": "alliances",
        "allies": "alliances",
        "client": "clients",
        "clients": "clients",
        "drive": "drives",
        "drives": "drives",
        "enemy": "enemies",
        "enemies": "enemies",
        "foe": "enemies",
        "foes": "enemies",
        "home": "home",
        "origin": "home",
    }
    return aliases.get(key, key)


def compact_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def limit_generated_evidence(value: str, max_length: int = GENERATED_EVIDENCE_MAX_LENGTH) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) <= max_length:
        return cleaned
    sentences = split_sentences(cleaned)
    if sentences and len(sentences[0]) <= max_length:
        return sentences[0]
    return cleaned[: max_length - 3].rstrip() + "..."


def required_stats_present(headers: list[str]) -> bool:
    return any(header in headers for header in ["name", "level", "race", "class"])


def parse_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [clean_table_cell(cell) for cell in stripped.strip("|").split("|")]


def normalize_stat_key(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def clean_table_cell(value: str) -> str:
    return value.strip().strip("-").strip()


def split_stat_values(value: str) -> list[str]:
    values = []
    for item in re.split(r"[;\n,]+", value):
        cleaned = item.strip()
        if cleaned and cleaned not in values:
            values.append(cleaned)
    return values


def attribute_connections(
    primary_name: str,
    stats: dict[str, str],
    text: str,
) -> list[tuple[str, str, str, str]]:
    relationships: list[tuple[str, str, str, str]] = []
    name_parts = [part for part in re.split(r"[\s_]+", primary_name.strip()) if part]
    family_name = name_parts[-1] if len(name_parts) > 1 else ""
    if family_name:
        relationships.append(
            (
                "family",
                "Family",
                family_name,
                f"{family_name} is inferred as the family name from the full character name {primary_name}.",
            )
        )
    for relationship_type, label, stat_key in [
        ("race", "Race", "race"),
        ("class", "Class", "class"),
        ("home", "Home", "home"),
    ]:
        raw_value = stats.get(stat_key, "")
        if stat_key in stats:
            value = clean_attribute_value(raw_value)
            relationships.append(
                (
                    relationship_type,
                    label,
                    value,
                    build_stat_evidence(label, value),
                )
            )
    for drive in split_stat_values(stats.get("drives", "") or stats.get("drive", "")):
        value = clean_attribute_value(drive)
        relationships.append(
            (
                "drive",
                "Drive",
                value,
                build_stat_evidence("Drive", value),
            )
        )
    return relationships


def character_relationships(
    primary_name: str,
    stats: dict[str, str],
    text: str,
) -> list[tuple[str, str, str, str]]:
    relationships: list[tuple[str, str, str, str]] = []
    relationship_columns = [
        ("client", "Client", ["clients", "client"]),
        ("ally", "Ally", ["allies", "alliances", "ally"]),
        ("rival", "Rivals", ["rivals", "rival"]),
        ("enemy", "Enemy", ["enemies", "enemy"]),
        ("lover", "Lover", ["lovers", "lover"]),
    ]
    for relationship_type, label, stat_keys in relationship_columns:
        raw_value = next((stats.get(key, "") for key in stat_keys if key in stats and stats.get(key, "").strip()), "")
        for value in split_stat_values(raw_value):
            cleaned_value = clean_relationship_target_value(value) or "Unknown"
            inferred_type = "client" if "client" in value.lower() else relationship_type
            inferred_label = "Client" if inferred_type == "client" else label
            relationships.append(
                (
                    inferred_type,
                    inferred_label,
                    cleaned_value,
                    build_stat_evidence(inferred_label, cleaned_value),
                )
            )
    relationships.extend(
        scope_unnamed_family_relationship(primary_name, relationship)
        for relationship in infer_unnamed_character_relationships(text)
    )
    return relationships


def scope_unnamed_family_relationship(
    primary_name: str,
    relationship: tuple[str, str, str, str],
) -> tuple[str, str, str, str]:
    relationship_type, label, value, evidence = relationship
    if relationship_type != "family" or value.lower() not in {"mother", "father", "parent"}:
        return relationship
    return relationship_type, label, f"{primary_name}'s {value}", evidence


def infer_primary_name(text: str, fallback: str, stats: dict[str, str] | None = None) -> str:
    heading = HEADING_PATTERN.search(text)
    if heading:
        title = strip_autogenerated_title_marker(heading.group(1).strip())
        if title:
            return title
    stat_name = (stats or {}).get("name", "").strip()
    if stat_name:
        return stat_name
    names = NAME_PATTERN.findall(text)
    return names[0] if names else fallback.replace("_", " ").title()


def strip_autogenerated_title_marker(title: str) -> str:
    return re.sub(r"\s*[-:|]\s*autogenerated\s*$", "", title, flags=re.IGNORECASE).strip()


def character_last_name(primary_name: str) -> str:
    parts = [part for part in re.split(r"[\s_]+", primary_name.strip()) if part]
    return parts[-1] if len(parts) > 1 else ""


def find_mentioned_names(text: str, primary_name: str, stats: dict[str, str] | None = None) -> list[str]:
    blocked = {
        "Character Stats",
        "Character Backstory",
        "Character Summary",
        "Clients",
        "Favorite Color",
        "Name Level Race Class Pronouns",
        "BACKSTORY",
        "SUMMARY",
    }
    primary_aliases = primary_name_aliases(primary_name, stats)
    names: list[str] = []
    normalized_text = normalize_honorific_periods(text)
    for candidate in NAME_PATTERN.findall(normalized_text):
        cleaned = clean_name_candidate(candidate)
        if cleaned in blocked or normalize_name_ref(cleaned) in primary_aliases:
            continue
        if not is_probable_name(cleaned):
            continue
        if cleaned not in names:
            names.append(cleaned)
    return remove_name_fragments(names)


def remove_name_fragments(names: list[str]) -> list[str]:
    long_name_parts = {
        normalize_name_ref(part)
        for name in names
        if len(name.split()) > 1
        for part in name.split()
    }
    return [
        name
        for name in names
        if len(name.split()) > 1 or normalize_name_ref(name) not in long_name_parts
    ]


def normalize_honorific_periods(text: str) -> str:
    return re.sub(r"\b(Mr|Mrs|Ms|Mx|Dr)\.", r"\1", text)


def clean_name_candidate(value: str) -> str:
    parts = [part for part in value.strip().split() if part]
    while parts and parts[0].strip(".") in HONORIFIC_WORDS:
        parts.pop(0)
    return " ".join(parts)


def find_place_mentions(text: str) -> list[tuple[str, list[str], list[str]]]:
    sentences = split_sentences(text)
    candidates: list[str] = []
    for candidate in NAME_PATTERN.findall(text):
        cleaned = candidate.strip()
        if is_probable_place(cleaned) and cleaned not in candidates:
            candidates.append(cleaned)

    canonical_places: list[str] = []
    aliases_by_place: dict[str, list[str]] = {}
    for candidate in sorted(candidates, key=lambda value: (-len(value), value.lower())):
        existing = next(
            (
                place
                for place in canonical_places
                if is_place_alias(candidate, place) or is_place_alias(place, candidate)
            ),
            "",
        )
        if existing:
            if candidate != existing and candidate not in aliases_by_place[existing]:
                aliases_by_place[existing].append(candidate)
            continue
        canonical_places.append(candidate)
        aliases_by_place[candidate] = []

    for place in canonical_places:
        first_word = place.split()[0]
        if first_word != place and re.search(rf"\b{re.escape(first_word)}\b", text) and first_word not in aliases_by_place[place]:
            aliases_by_place[place].append(first_word)

    return [
        (place, sorted(aliases_by_place[place]), evidence_for_place(sentences, place, aliases_by_place[place]))
        for place in canonical_places
    ]


def is_probable_place(value: str) -> bool:
    if not is_probable_name(value):
        return False
    lowered = value.lower()
    if lowered in GENERIC_PLACE_NAMES:
        return False
    if any(lowered.endswith(suffix.lower()) for suffix in PLACE_SUFFIXES):
        return True
    return bool(re.search(r"\b(?:academy|college|coast|halls?|sea|shores?|tower|village)\b", lowered))


def is_place_alias(candidate: str, canonical: str) -> bool:
    candidate_norm = normalize_name_ref(candidate)
    canonical_norm = normalize_name_ref(canonical)
    if not candidate_norm or not canonical_norm or candidate_norm == canonical_norm:
        return True
    return canonical_norm.startswith(candidate_norm) or candidate_norm.startswith(canonical_norm)


def evidence_for_place(sentences: list[str], place: str, aliases: list[str]) -> list[str]:
    refs = [place, *aliases]
    evidence = [
        sentence
        for sentence in sentences
        if any(ref in sentence or ref.lower() in sentence.lower() for ref in refs)
    ]
    return evidence[:5]


def infer_place_type(place_name: str) -> str:
    lowered = place_name.lower()
    if "college" in lowered or "academy" in lowered:
        return "school"
    if "coast" in lowered or "sea" in lowered or "shore" in lowered:
        return "region"
    return "place"


def build_place_summary(primary_name: str, place_name: str, evidence: list[str]) -> str:
    evidence_text = " ".join(evidence[:2])
    return f"{place_name} is a place connected to {primary_name}. Evidence: {evidence_text}"


def is_known_place_reference(name: str, places: dict[str, PlaceNode]) -> bool:
    normalized = normalize_name_ref(name)
    for place in places.values():
        refs = [place.name, *place.aliases]
        if any(normalized == normalize_name_ref(ref) for ref in refs):
            return True
    return False


def primary_name_aliases(primary_name: str, stats: dict[str, str] | None = None) -> set[str]:
    aliases = {normalize_name_ref(primary_name)}
    for part in re.split(r"[\s_]+", primary_name):
        if part:
            aliases.add(normalize_name_ref(part))
    stat_name = (stats or {}).get("name", "")
    if stat_name:
        aliases.add(normalize_name_ref(stat_name))
        for part in re.split(r"[\s_]+", stat_name):
            if part:
                aliases.add(normalize_name_ref(part))
    return aliases


def normalize_name_ref(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def split_sentences(text: str) -> list[str]:
    sentences = []
    normalized_text = normalize_honorific_periods(text.replace("\r\n", "\n"))
    for match in SENTENCE_PATTERN.findall(normalized_text):
        sentence = " ".join(match.strip().split())
        if sentence and not sentence.startswith("|") and not sentence.startswith("#"):
            sentences.append(sentence)
    return sentences


def evidence_for_name(sentences: list[str], name: str) -> list[str]:
    parts = name.split()
    first_name = parts[0]
    family_name = parts[-1] if len(parts) > 1 else ""
    refs = [name, first_name]
    if family_name:
        refs.append(family_name)
    evidence = [
        sentence
        for sentence in sentences
        if any(ref in sentence or ref.lower() in sentence.lower() for ref in refs)
    ]
    return evidence[:5]


def infer_relationship(
    source_id: str,
    target_id: str,
    target_name: str,
    evidence: list[str],
) -> RelationshipEdge | None:
    evidence_text = " ".join(evidence).lower()
    target_pattern = re.escape(target_name)
    for relationship_type, relationship_label, sentiment, keywords in RELATIONSHIP_RULES:
        if relationship_type == "betrayer" and not re.search(
            rf"\b{target_pattern}\b[^.!?]*\bbetray",
            " ".join(evidence),
            re.IGNORECASE,
        ):
            continue
        if relationship_type == "former_mentor" and not re.search(
            rf"\b{target_pattern}\b[^.!?]*\b(?:trained|teacher|mentor)",
            " ".join(evidence),
            re.IGNORECASE,
        ):
            continue
        if relationship_type == "rival" and not re.search(
            rf"\b{target_pattern}\b[^.!?]*\brival",
            " ".join(evidence),
            re.IGNORECASE,
        ):
            continue
        if relationship_type == "family":
            family_target = target_name.strip().lower() in {
                "sister",
                "brother",
                "mother",
                "father",
                "parent",
                "child",
                "family",
            }
            family_name_pattern = re.search(
                rf"(?:\b(?:sister|brother|mother|father|parent|child|family)\b[^.!?]*\b{target_pattern}\b|\b{target_pattern}\b\s*,?\s*(?:a|an|the|his|her|their)?\s*\b(?:sister|brother|mother|father|parent|child)\b)",
                " ".join(evidence),
                re.IGNORECASE,
            )
            if not family_target and not family_name_pattern:
                continue
        if any(keyword in evidence_text for keyword in keywords):
            conflict_level = 0.7 if sentiment == "hostile" else 0.3 if sentiment == "complicated" else 0.0
            trust_level = 0.25 if sentiment == "hostile" else 0.45 if sentiment == "complicated" else 0.75
            return RelationshipEdge(
                source=source_id,
                target=target_id,
                relationship_type=relationship_type,
                relationship_label=relationship_label,
                sentiment=sentiment,
                trust_level=trust_level,
                conflict_level=conflict_level,
                emotional_weight=0.8,
                evidence=evidence,
            )
    return None


def dedupe_relationships(relationships: list[RelationshipEdge]) -> list[RelationshipEdge]:
    deduped: list[RelationshipEdge] = []
    by_key: dict[tuple[str, str, str], RelationshipEdge] = {}
    for relationship in relationships:
        key = (relationship.source, relationship.target, relationship.relationship_type)
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = relationship
            deduped.append(relationship)
            continue
        for evidence in relationship.evidence:
            if evidence not in existing.evidence:
                existing.evidence.append(evidence)
    return deduped


def build_related_summary(name: str, primary_name: str, relationship: RelationshipEdge, evidence: list[str]) -> str:
    evidence_text = " ".join(evidence[:2])
    return (
        f"{name} is connected to {primary_name} as {relationship.relationship_label.lower()}. "
        f"Source evidence says: {evidence_text}"
    )


def build_metadata_summary(primary_name: str, label: str, value: str, evidence: str) -> str:
    if not value:
        return f"{primary_name}'s {label.lower()} is not specified. Evidence: {evidence}"
    return f"{primary_name}'s {label.lower()} is {value}. Evidence: {evidence}"


def clean_attribute_value(value: str) -> str:
    cleaned = value.strip()
    if cleaned.lower() in UNKNOWN_VALUES:
        return ""
    return cleaned


def clean_relationship_target_value(value: str) -> str:
    cleaned = clean_attribute_value(value).rstrip(".")
    if not cleaned:
        return ""
    normalized = normalize_honorific_periods(cleaned)
    for candidate in NAME_PATTERN.findall(normalized):
        candidate = candidate.strip()
        if candidate.split()[0].strip(".") in HONORIFIC_WORDS or is_probable_name(candidate):
            return candidate
    return cleaned


def infer_unnamed_character_relationships(text: str) -> list[tuple[str, str, str, str]]:
    relationships: list[tuple[str, str, str, str]] = []
    family_patterns = [
        ("mother", "Mother", r"\b(?:her|his|their|the)\s+mother\b"),
        ("father", "Father", r"\b(?:her|his|their|the)\s+father\b"),
        ("parent", "Parent", r"\b(?:her|his|their|the)\s+parent\b"),
    ]
    lowered_text = text.lower()
    for family_role, value, pattern in family_patterns:
        if not re.search(pattern, lowered_text, re.IGNORECASE):
            continue
        evidence = evidence_for_pattern(text, pattern)
        relationships.append(
            (
                "family",
                "Family",
                value,
                evidence or f"An unnamed {family_role} is mentioned in the backstory.",
            )
        )
    return relationships


def build_stat_evidence(label: str, value: str) -> str:
    if value:
        return f"{label} is listed as {value} in the Character Stats table."
    return f"{label} is present in the Character Stats table but has no known value."


def evidence_for_pattern(text: str, pattern: str) -> str:
    for sentence in split_sentences(text):
        if re.search(pattern, sentence, re.IGNORECASE):
            return sentence
    return ""


def is_probable_name(value: str) -> bool:
    parts = value.split()
    if not parts:
        return False
    if parts[0].strip(".") in HONORIFIC_WORDS:
        return False
    if parts[0] in NON_NAME_WORDS:
        return False
    if any(part.lower() in UNKNOWN_VALUES for part in parts):
        return False
    if any(part in {"Character", "Stats", "Backstory", "Summary"} for part in parts):
        return False
    return True


def unique_node_id(existing: dict[str, AttributeNode], base_id: str) -> str:
    if base_id not in existing:
        return base_id
    index = 2
    while f"{base_id}_{index}" in existing:
        index += 1
    return f"{base_id}_{index}"


def unique_character_id(existing: dict[str, CharacterNode], base_id: str) -> str:
    if base_id not in existing:
        return base_id
    index = 2
    while f"{base_id}_{index}" in existing:
        index += 1
    return f"{base_id}_{index}"


def unique_place_id(existing: dict[str, PlaceNode], base_id: str) -> str:
    if base_id not in existing:
        return base_id
    index = 2
    while f"{base_id}_{index}" in existing:
        index += 1
    return f"{base_id}_{index}"


def extract_primary_summary(text: str, primary_name: str) -> str:
    summary_match = re.search(r"## Character Summary\s+(?P<summary>.+)$", text, re.IGNORECASE | re.DOTALL)
    if summary_match:
        summary = " ".join(summary_match.group("summary").strip().split())
        if summary:
            return summary
    sentences = split_sentences(text)
    for sentence in sentences:
        if primary_name.split()[0] in sentence:
            return sentence
    return f"{primary_name} is the primary character. No concise summary was found in the source backstory."


def extract_motivations(text: str) -> list[str]:
    motivations: list[str] = []
    for pattern in MOTIVATION_PATTERNS:
        for match in pattern.finditer(text):
            motivation = match.group(1).strip(" .")
            if motivation and motivation not in motivations:
                motivations.append(motivation)
    return motivations[:5]


def extract_traits(text: str) -> list[str]:
    lowered = text.lower()
    traits = [trait for trait in sorted(TRAIT_WORDS) if trait in lowered]
    return traits[:8]


def extract_alignment(text: str) -> Alignment:
    faction_alignment = sorted(set(re.findall(r"\b(?:anti-[A-Z][A-Za-z ]+|exiled [a-z ]+|Silver Court)\b", text)))
    opposition_targets = [target for target in faction_alignment if target.lower().startswith("anti-")]
    return Alignment(
        moral_alignment="unknown",
        faction_alignment=faction_alignment,
        loyalty_targets=[],
        opposition_targets=opposition_targets,
    )


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "unknown"
