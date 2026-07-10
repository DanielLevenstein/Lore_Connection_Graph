import json

from character_graph.extraction import extract_character_graph
from character_graph.graph_view import attribute_rows, evidence_rows, place_rows, relationship_dot, relationship_rows
from character_graph.ingest import load_backstory
from character_graph.prompt_context import build_prompt_context
from character_graph.retrieval import retrieve_relevant_context
from character_graph.storage import load_graph, save_graph
from character_graph.validation import validate_graph


BACKSTORY = """# Arlen Voss

## Character Stats

| Name | Level | Race | Class | Pronouns | Drives | Alliances | Enemies |
|------|-------|------|-------|----------|--------|-----------|---------|
| Arlen | 3 | Elf | Wizard | he/him | restore his family name; avoid becoming like his father | old household retainers | Silver Court; Torvak |

## Character Backstory

Mirelle trained Arlen before betraying him to the Silver Court.
Torvak is a rival mercenary who knows Arlen's old routes.
Arlen wants to restore his family name and avoid becoming like his father.

## Character Summary

Arlen is guarded, strategic, and loyal once trust is earned.
"""

MINIMAL_BACKSTORY = """# Arlen Voss

## Character Stats

| Name | Race | Class |
|------|------|-------|
| Arlen | Elf | Wizard |

## Character Backstory

Arlen keeps his plans quiet.
"""


def test_load_backstory_computes_source_hash(tmp_path):
    source = tmp_path / "arlen.md"
    source.write_text(BACKSTORY, encoding="utf-8")

    document = load_backstory(source, character_id="arlen_voss")

    assert document.character_id == "arlen_voss"
    assert document.source_file == str(source)
    assert document.raw_text == BACKSTORY
    assert len(document.source_hash) == 64


def test_extract_character_graph_creates_stats_and_known_prose_relationships(tmp_path):
    source = tmp_path / "arlen.md"
    source.write_text(BACKSTORY, encoding="utf-8")
    document = load_backstory(source, character_id="arlen_voss")

    graph = extract_character_graph(document)

    assert graph.primary_character.name == "Arlen Voss"
    assert "arlen_voss" in graph.characters
    assert {"arlen_voss", "mirelle", "old_household_retainers", "silver_court", "torvak"} <= set(graph.characters)
    assert {
        "family_voss",
        "race_elf",
        "class_wizard",
    } <= set(graph.attributes)
    assert "enemy_torvak" not in graph.attributes
    assert "silver_court" in graph.places
    assert {
        edge.relationship_type for edge in graph.relationships
    } == {
        "family",
        "race",
        "class",
        "drive",
        "ally",
        "enemy",
        "place",
        "betrayer",
        "rival",
    }
    assert all(edge.relationship_type != "unknown" for edge in graph.relationships)
    assert all(edge.relationship_label.lower() != "unknown" for edge in graph.relationships)
    assert all(attribute.attribute_type.lower() != "unknown" for attribute in graph.attributes.values())
    race_edge = next(edge for edge in graph.relationships if edge.relationship_type == "race")
    assert graph.attributes[race_edge.target].value == "Elf"
    assert "Character Stats table" in race_edge.evidence[0]
    assert graph.embeddings[race_edge.target].vector
    enemy_edges = [edge for edge in graph.relationships if edge.relationship_type == "enemy"]
    assert {edge.target for edge in enemy_edges} == {"silver_court", "torvak"}
    assert any(edge.relationship_type == "betrayer" and edge.target == "mirelle" for edge in graph.relationships)
    assert any(edge.relationship_type == "rival" and edge.target == "torvak" for edge in graph.relationships)


def test_extract_character_graph_accepts_minimal_character_stats_table(tmp_path):
    source = tmp_path / "arlen.md"
    source.write_text(MINIMAL_BACKSTORY, encoding="utf-8")

    graph = extract_character_graph(load_backstory(source, character_id="arlen_voss"))

    assert set(graph.characters) == {"arlen_voss"}
    assert {"family_voss", "race_elf", "class_wizard"} <= set(graph.attributes)
    assert {edge.relationship_type for edge in graph.relationships} == {"family", "race", "class"}


def test_extract_character_graph_reads_drives_alliances_and_enemies_from_details(tmp_path):
    source = tmp_path / "neal.md"
    source.write_text(
        """# Neal Lovington

## Character Stats

| Name | Race | Class |
| ---- | ---- | ----- |
| Neal | Elf | Bard |

## Character Backstory

Neal performs at the Royal Tittles.

## Character Summary

Neal is a bard with complicated regulars.

### Character Details

| Field | Description |
| ----- | ----------- |
| Drive | Entertaining sailors on shore leave. |
| Alliances | Jory Ravenmark is their favorite client. |
| Enemies | Mrs Nighbloom was not happy. |
""",
        encoding="utf-8",
    )

    graph = extract_character_graph(load_backstory(source, character_id="neal_lovington"))

    assert "drive_entertaining_sailors_on_shore_leave" in graph.attributes
    assert graph.attributes["drive_entertaining_sailors_on_shore_leave"].value == "Entertaining sailors on shore leave."
    assert any(edge.relationship_type == "drive" for edge in graph.relationships)
    assert any(
        edge.relationship_type == "client" and graph.characters[edge.target].name == "Jory Ravenmark is their favorite client."
        for edge in graph.relationships
    )
    assert any(
        edge.relationship_type == "enemy" and graph.characters[edge.target].name == "Mrs Nighbloom was not happy."
        for edge in graph.relationships
    )


def test_extract_character_graph_loads_character_connections_table(tmp_path):
    source = tmp_path / "mara.md"
    source.write_text(
        """# Mara Voss

## Character Stats

| Name | Race | Class |
| ---- | ---- | ----- |
| Mara | Elf | Wizard |

## Character Backstory

Mara keeps careful notes.

## Character Summary

Mara is careful.

## Character Connections

| Source | Relationship | Name | Evidence |
| ------ | ------------ | ---- | -------- |
| Character Sheet | Ally | Jory Ravenmark | Jory guarded Mara on the west road. |
| Place | Place | Royal Tittles | Mara met Jory at Royal Tittles. |
""",
        encoding="utf-8",
    )

    graph = extract_character_graph(load_backstory(source, character_id="mara_voss"))

    assert "jory_ravenmark" in graph.characters
    assert graph.characters["jory_ravenmark"].name == "Jory Ravenmark"
    assert "royal_tittles" in graph.places
    assert any(edge.relationship_type == "ally" and edge.target == "jory_ravenmark" for edge in graph.relationships)
    assert any(edge.relationship_type == "place" and edge.target == "royal_tittles" for edge in graph.relationships)


def test_extract_character_graph_loads_legacy_character_connections_table_and_limits_evidence(tmp_path):
    source = tmp_path / "orin.md"
    long_evidence = (
        "Jory Ravenmark helped Orin escape the docks. "
        + "This extra generated evidence sentence is intentionally verbose and repetitive. " * 8
    )
    source.write_text(
        f"""# Orin Nightbloom

## Character Stats

| Name | Race | Class |
| ---- | ---- | ----- |
| Orin | Half-Orc | Bard |

## Character Backstory

Orin sings against old curses.

## Character Summary

Orin is haunted.

### Character Connections

| Table | Item | Value | Evidence |
| ----- | ---- | ----- | -------- |
| Relationships | Ally | Jory Ravenmark | {long_evidence} |
| Attributes | Drive | break a curse | The drive is listed in the old generated table. |
| Places | Tavern | Royal Tittles | Orin performs at Royal Tittles. |
""",
        encoding="utf-8",
    )

    graph = extract_character_graph(load_backstory(source, character_id="orin_nightbloom"))

    ally_edge = next(edge for edge in graph.relationships if edge.relationship_type == "ally")
    assert graph.characters[ally_edge.target].name == "Jory Ravenmark"
    assert len(ally_edge.evidence[0]) <= 240
    assert ally_edge.evidence[0] == "Jory Ravenmark helped Orin escape the docks."
    assert any(attribute.attribute_type == "Drive" and attribute.value == "break a curse" for attribute in graph.attributes.values())
    assert any(place.name == "Royal Tittles" and place.place_type == "tavern" for place in graph.places.values())


def test_extract_character_graph_keeps_honorific_client_names_together(tmp_path):
    source = tmp_path / "neal.md"
    source.write_text(
        """# Neal Lovington

## Character Stats

| Name | Race | Class |
| ---- | ---- | ----- |
| Mx. Lovington | Elf | Bard |

## Character Backstory

One of these clients was Mr. Nightbloom. Orin Nightbloom was haunted by the loss of his mother.
But Neals favorite client was actually Ms. Ravenmark. Jory Ravenmark was a lonely woman who worked in the shoreline lighthouse.

## Character Summary

Neal works with private clients.
""",
        encoding="utf-8",
    )

    graph = extract_character_graph(load_backstory(source, character_id="neal_lovington"))
    client_names = {
        graph.characters[edge.target].name
        for edge in graph.relationships
        if edge.relationship_type == "client" and edge.target in graph.characters
    }

    assert "Jory Ravenmark" in client_names
    assert "Orin Nightbloom" in client_names
    assert not any(
        edge.relationship_type == "family" and edge.target in graph.characters and graph.characters[edge.target].name in client_names
        for edge in graph.relationships
    )


def test_extract_character_graph_skips_unknown_prose_relationships(tmp_path):
    source = tmp_path / "arlen.md"
    source.write_text(
        """# Arlen Voss

## Character Stats

| Name | Race | Class |
|------|------|-------|
| Arlen | Elf | Wizard |

## Character Backstory

Mara passed through town once.
Joren owned a blue cloak.
""",
        encoding="utf-8",
    )

    graph = extract_character_graph(load_backstory(source, character_id="arlen_voss"))

    assert set(graph.characters) == {"arlen_voss"}
    assert all(edge.relationship_type != "unknown" for edge in graph.relationships)


def test_extract_character_graph_filters_sentence_starters_and_unknown_attributes(tmp_path):
    source = tmp_path / "jory.md"
    source.write_text(
        """# Jory Ravenmark

## Character Stats

| Name | Race | Class | Pronouns |
|------|------|-------|----------|
| Jory | Human | Barbarian | Unknown |

## Character Backstory

Haunted by the loss of her family and the inexplicable mercy shown by a monster, Jory took to the sea.
Her mother died at sea and her father was consumed by loneliness.
When she was still but a child a monster attacked the watchtower.
That night Jory decided to dedicate her life to tracking down the beast.
She learned to read the open sea as her father once had before her.
""",
        encoding="utf-8",
    )

    graph = extract_character_graph(load_backstory(source, character_id="jory_ravenmark"))

    assert "haunted" not in graph.characters
    assert "her" not in graph.characters
    assert "when" not in graph.characters
    assert "that" not in graph.characters
    assert "she" not in graph.characters
    assert "pronouns_unknown" not in graph.attributes
    assert graph.attributes["family_ravenmark"].value == "Ravenmark"
    assert graph.characters["mother"].name == "Mother"
    assert graph.characters["father"].name == "Father"
    assert any(edge.relationship_type == "family" and edge.target == "mother" for edge in graph.relationships)
    assert any(edge.relationship_type == "family" and edge.target == "father" for edge in graph.relationships)


def test_extract_character_graph_does_not_create_self_family_edge_for_underscored_heading(tmp_path):
    source = tmp_path / "jory.md"
    source.write_text(
        """# Jory_Ravenmark

## Character Stats

| Name | Race | Class |
|------|------|-------|
| Jory | Human | Barbarian |

## Character Backstory

Haunted by the loss of her family and the inexplicable mercy shown by a monster, Jory took to the sea.
""",
        encoding="utf-8",
    )

    graph = extract_character_graph(load_backstory(source, character_id="jory_ravenmark"))

    assert "jory" not in graph.characters
    assert not any(edge.relationship_type == "family" and edge.target == "jory" for edge in graph.relationships)
    assert "ravenmark" not in graph.characters
    assert graph.attributes["family_ravenmark"].value == "Ravenmark"


def test_graph_storage_round_trips_json(tmp_path):
    source = tmp_path / "arlen.md"
    graph_path = tmp_path / "arlen.graph.json"
    source.write_text(BACKSTORY, encoding="utf-8")
    graph = extract_character_graph(load_backstory(source, character_id="arlen_voss"))

    save_graph(graph, graph_path)
    loaded = load_graph(graph_path)

    assert loaded is not None
    assert loaded.to_dict() == json.loads(graph_path.read_text(encoding="utf-8"))
    assert loaded.attributes["race_elf"].value == "Elf"


def test_graph_storage_migrates_legacy_attribute_nodes(tmp_path):
    graph_path = tmp_path / "legacy.graph.json"
    graph_path.write_text(
        json.dumps(
            {
                "schema_version": "0.1.0",
                "primary_character": {
                    "id": "arlen_voss",
                    "name": "Arlen Voss",
                    "source_file": "characters/arlen.md",
                },
                "characters": {
                    "arlen_voss": {
                        "name": "Arlen Voss",
                        "aliases": [],
                        "role": "primary character",
                        "summary": "Arlen is guarded.",
                        "motivations": [],
                        "traits": [],
                        "alignment": {},
                        "source_spans": [],
                    },
                    "pronouns_he_him": {
                        "name": "he/him",
                        "aliases": [],
                        "role": "Pronouns",
                        "summary": "Arlen Voss's pronouns are he/him.",
                        "motivations": [],
                        "traits": [],
                        "alignment": {},
                        "source_spans": ["Pronouns are listed as he/him in the Character Stats table."],
                    },
                },
                "relationships": [
                    {
                        "source": "arlen_voss",
                        "target": "pronouns_he_him",
                        "relationship_type": "pronouns",
                        "relationship_label": "Pronouns",
                        "sentiment": "metadata",
                        "trust_level": 1.0,
                        "conflict_level": 0.0,
                        "emotional_weight": 0.3,
                        "evidence": ["Pronouns are listed as he/him in the Character Stats table."],
                    }
                ],
                "metadata": {
                    "created_at": "2026-07-08T00:00:00",
                    "updated_at": "2026-07-08T00:00:00",
                    "source_hash": "hash",
                },
            }
        ),
        encoding="utf-8",
    )

    loaded = load_graph(graph_path)

    assert loaded is not None
    assert set(loaded.characters) == {"arlen_voss"}
    assert loaded.attributes["pronouns_he_him"].value == "he/him"
    assert loaded.attributes["pronouns_he_him"].attribute_type == "Pronouns"


def test_retrieval_formats_related_character_context(tmp_path):
    source = tmp_path / "arlen.md"
    source.write_text(BACKSTORY, encoding="utf-8")
    graph = extract_character_graph(load_backstory(source, character_id="arlen_voss"))

    retrieved = retrieve_relevant_context(graph, "What does being an Elf Wizard mean for me?")
    context = build_prompt_context(retrieved)

    assert retrieved[0].display_name in {"Elf", "Wizard"}
    assert "Relevant character attribute context:" in context
    assert "Relationship metadata:" in context


def test_validation_warns_on_missing_relationship_target(tmp_path):
    source = tmp_path / "arlen.md"
    source.write_text(BACKSTORY, encoding="utf-8")
    graph = extract_character_graph(load_backstory(source, character_id="arlen_voss"))
    graph.relationships[0].target = "missing"

    warnings = validate_graph(graph)

    assert "Relationship target `missing` is missing from graph nodes." in warnings


def test_graph_view_helpers_format_relationships_and_dot(tmp_path):
    source = tmp_path / "arlen.md"
    source.write_text(BACKSTORY, encoding="utf-8")
    graph = extract_character_graph(load_backstory(source, character_id="arlen_voss"))

    relationships = relationship_rows(graph)
    attributes = attribute_rows(graph)
    places = place_rows(graph)
    evidence = evidence_rows(graph)
    dot = relationship_dot(graph)

    assert all("Evidence" not in row for row in relationships)
    assert all(row["Relationship"] not in {"Race", "Class", "Pronouns", "Drive"} for row in relationships)
    assert any(row["Value"] == "Elf" and row["Attribute"] == "Race" for row in attributes)
    assert any(row["Value"] == "Silver Court" and row["Attribute"] == "Place" for row in places)
    assert any(row["Table"] == "Relationships" and row["Item"] == "Rival" for row in evidence)
    assert any(row["Table"] == "Attributes" and row["Item"] == "Race" for row in evidence)
    assert any(row["Table"] == "Places" and row["Value"] == "Silver Court" for row in evidence)
    assert not any(row["Item"] == "Pronouns" for row in evidence)
    assert "digraph CharacterRelationships" in dot
    assert '"arlen_voss" -> "race_elf"' in dot
    assert 'shape="ellipse"' in dot


def test_extract_character_graph_routes_place_evidence_away_from_family_relationships(tmp_path):
    source = tmp_path / "orin.md"
    source.write_text(
        """# Orin Stonehand

## Character Stats

| Name | Race | Class |
|------|------|-------|
| Orin | Half-orc | Wizard |

## Character Backstory

Orin was born with a weight the world seldom places on a child, the weight of a half-orc heritage clashing with the refined air of the Sunstone Mage College nestled on the frosted coast of his life.
The Sunstone mages, haunted by the specter of his mother's fate, urged him to abandon his search, to leave the cursed echoes at his blood-burdened doorstep.
He carries the weight of the Sunstone mage college, a living monument to the pain their whispers could not heal, and a beacon for the path that could.
""",
        encoding="utf-8",
    )

    graph = extract_character_graph(load_backstory(source, character_id="orin_stonehand"))
    evidence = evidence_rows(graph)

    assert graph.places["sunstone_mage_college"].name == "Sunstone Mage College"
    assert graph.places["sunstone_mage_college"].aliases == ["Sunstone"]
    assert any(row["Table"] == "Places" and row["Value"] == "Sunstone Mage College" for row in evidence)
    assert not any(
        row["Table"] == "Relationships" and row["Item"] == "Family" and "Sunstone" in row["Value"]
        for row in evidence
    )
