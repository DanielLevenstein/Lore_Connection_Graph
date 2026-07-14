from character_graph.combined_graph import (
    build_combined_character_graph,
    combined_attribute_rows,
    combined_relationship_dot,
    combined_relationship_rows,
)
from character_graph.extraction import extract_character_graph
from character_graph.ingest import load_backstory
from character_graph.schema import AttributeNode, CharacterGraph, CharacterNode, PrimaryCharacterRef, RelationshipEdge
import local_chatbot.storage as storage
from local_chatbot.storage import Character, append_character_connections, read_character_profile


def graph_from_text(tmp_path, filename: str, text: str):
    path = tmp_path / filename
    path.write_text(text, encoding="utf-8")
    return extract_character_graph(load_backstory(path, character_id=path.stem))


def test_combined_graph_links_existing_and_secondary_characters(tmp_path):
    neal = graph_from_text(
        tmp_path,
        "Neal_Lovington.md",
        """# Neal Lovington

## Character Stats

| Name | Race | Class |
| ---- | ---- | ----- |
| Neal | Elf | Bard |

## Character Backstory

Jory Ravenmark is their favorite client. Mira Vale is a trusted ally.

## Character Summary

Neal knows everyone by their favorite song.
""",
    )
    jory = graph_from_text(
        tmp_path,
        "Jory_Ravenmark.md",
        """# Jory Ravenmark

## Character Stats

| Name | Race | Class |
| ---- | ---- | ----- |
| Jory | Human | Barbarian |

## Character Backstory

Jory trusts Neal.

## Character Summary

Jory is a sailor.
""",
    )

    combined = build_combined_character_graph([neal, jory])

    assert ("neal_lovington", "jory_ravenmark", "client") in {
        (edge.source, edge.target, edge.relationship_type) for edge in combined.edges
    }
    assert "mira_vale" in combined.characters
    assert combined.characters["mira_vale"].name == "Mira Vale"


def test_combined_graph_rows_and_dot_include_place_nodes(tmp_path):
    neal = graph_from_text(
        tmp_path,
        "Neal_Lovington.md",
        """# Neal Lovington

## Character Stats

| Name | Race | Class |
| ---- | ---- | ----- |
| Neal | Elf | Bard |

## Character Backstory

Neal performs at the Royal Tittles Tavern.

## Character Summary

Neal is a performer.
""",
    )
    combined = build_combined_character_graph(
        [neal],
        place_sources=[("royal_tittles", "Royal Tittles", "world_building/lore/places/Royal_Tittles.md")],
        lore_relationships=[
            {
                "source_id": "neal_lovington",
                "source_name": "Neal Lovington",
                "source_type": "character",
                "target_id": "royal_tittles",
                "target_name": "Royal Tittles",
                "target_type": "place",
                "relationship": "Performs",
                "evidence": "Neal performs at the Royal Tittles Tavern.",
            }
        ],
    )

    dot = combined_relationship_dot(combined)

    assert combined.characters["royal_tittles"].node_type == "place"
    assert "Royal Tittles" in dot
    assert 'shape="component"' in dot


def test_combined_graph_includes_family_names_without_other_attributes(tmp_path):
    neal = graph_from_text(
        tmp_path,
        "Neal_Lovington.md",
        """# Neal Lovington

## Character Stats

| Name | Race | Class | Drives |
| ---- | ---- | ----- | ------ |
| Neal | Elf | Bard | make a name |

## Character Backstory

Neal performs at the Royal Tittles Tavern.

## Character Summary

Neal is a performer.
""",
    )

    combined = build_combined_character_graph([neal])

    assert combined.characters["family_lovington"].name == "Lovington"
    assert combined.characters["family_lovington"].node_type == "family"
    assert ("neal_lovington", "family_lovington", "family") in {
        (edge.source, edge.target, edge.relationship_type) for edge in combined.edges
    }
    assert "race_elf" not in combined.characters
    assert "class_bard" not in combined.characters
    assert "drive_make_a_name" not in combined.characters


def test_combined_attribute_rows_include_hidden_metadata_with_evidence(tmp_path):
    neal = graph_from_text(
        tmp_path,
        "Neal_Lovington.md",
        """# Neal Lovington

## Character Stats

| Name | Race | Class | Drives |
| ---- | ---- | ----- | ------ |
| Neal | Elf | Bard | make a name; entertain sailors |

## Character Backstory

Neal performs at the Royal Tittles Tavern.

## Character Summary

Neal is a performer.
""",
    )

    rows = combined_attribute_rows([neal])

    assert {
        ("Neal Lovington", "Race", "Elf"),
        ("Neal Lovington", "Class", "Bard"),
        ("Neal Lovington", "Drive", "make a name"),
        ("Neal Lovington", "Drive", "entertain sailors"),
    } <= {(row["Character"], row["Attribute"], row["Value"]) for row in rows}
    assert not any(row["Attribute"] == "Family" for row in rows)
    assert all(row["Evidence"] for row in rows)


def test_combined_attribute_rows_replace_underscores_in_values(tmp_path):
    neal = graph_from_text(
        tmp_path,
        "Neal_Lovington.md",
        """# Neal Lovington

## Character Stats

| Name | Race | Class | Drives |
| ---- | ---- | ----- | ------ |
| Neal | Elf | Bard | entertain_sailors |

## Character Backstory

Neal performs at the Royal Tittles Tavern.
""",
    )

    rows = combined_attribute_rows([neal])

    assert any(row["Value"] == "entertain sailors" for row in rows)
    assert not any("_" in row["Value"] for row in rows)


def test_combined_attribute_rows_keep_each_character_metadata_separate(tmp_path):
    neal = graph_from_text(
        tmp_path,
        "Neal_Lovington.md",
        """# Neal Lovington

## Character Stats

| Name | Race | Class | Drives |
| ---- | ---- | ----- | ------ |
| Neal | Elf | Bard | entertain sailors |

## Character Backstory

Neal sings.

## Character Summary

Neal is a performer.
""",
    )
    jory = graph_from_text(
        tmp_path,
        "Jory_Ravenmark.md",
        """# Jory Ravenmark

## Character Stats

| Name | Race | Class | Drives |
| ---- | ---- | ----- | ------ |
| Jory | Human | Barbarian | chart the sea |

## Character Backstory

Jory sails.

## Character Summary

Jory is a sailor.
""",
    )

    rows = combined_attribute_rows([neal, jory])

    assert ("Neal Lovington", "Drive", "entertain sailors") in {
        (row["Character"], row["Attribute"], row["Value"]) for row in rows
    }
    assert ("Jory Ravenmark", "Drive", "chart the sea") in {
        (row["Character"], row["Attribute"], row["Value"]) for row in rows
    }


def test_combined_graph_keeps_unnamed_mothers_character_scoped(tmp_path):
    jory = graph_from_text(
        tmp_path,
        "Jory_Ravenmark.md",
        """# Jory Ravenmark

## Character Stats

| Name | Race | Class |
| ---- | ---- | ----- |
| Jory | Human | Barbarian |

## Character Backstory

Her mother died at sea.

## Character Summary

Jory is a sailor.
""",
    )
    orin = graph_from_text(
        tmp_path,
        "Orin_Nightbloom.md",
        """# Orin Nightbloom

## Character Stats

| Name | Race | Class |
| ---- | ---- | ----- |
| Orin | Half-Orc | Bard |

## Character Backstory

His mother taught him old tavern songs.

## Character Summary

Orin is haunted.
""",
    )

    combined = build_combined_character_graph([jory, orin])

    assert combined.characters["jory_ravenmark_s_mother"].name == "Jory Ravenmark's Mother"
    assert combined.characters["orin_nightbloom_s_mother"].name == "Orin Nightbloom's Mother"
    assert ("jory_ravenmark", "jory_ravenmark_s_mother", "family") in {
        (edge.source, edge.target, edge.relationship_type) for edge in combined.edges
    }
    assert ("orin_nightbloom", "orin_nightbloom_s_mother", "family") in {
        (edge.source, edge.target, edge.relationship_type) for edge in combined.edges
    }
    assert "mother" not in combined.characters


def test_combined_graph_does_not_match_possessive_family_nodes_to_primary_characters(tmp_path):
    jory = graph_from_text(
        tmp_path,
        "Jory_Ravenmark.md",
        """# Jory Ravenmark

## Character Stats

| Name | Race | Class |
| ---- | ---- | ----- |
| Jory | Human | Barbarian |

## Character Backstory

Jory remembers Orin Nightbloom's mother from the harbor.

## Character Summary

Jory is a sailor.
""",
    )
    orin = graph_from_text(
        tmp_path,
        "Orin_Nightbloom.md",
        """# Orin Nightbloom

## Character Stats

| Name | Race | Class |
| ---- | ---- | ----- |
| Orin | Half-Orc | Bard |

## Character Backstory

His mother taught him old tavern songs.

## Character Summary

Orin is haunted.
""",
    )

    combined = build_combined_character_graph([jory, orin])

    assert ("orin_nightbloom", "orin_nightbloom_s_mother", "family") in {
        (edge.source, edge.target, edge.relationship_type) for edge in combined.edges
    }
    assert ("orin_nightbloom", "jory_ravenmark", "family") not in {
        (edge.source, edge.target, edge.relationship_type) for edge in combined.edges
    }


def test_combined_graph_uses_family_node_shape_and_label_in_dot(tmp_path):
    neal = graph_from_text(
        tmp_path,
        "Neal_Lovington.md",
        """# Neal Lovington

## Character Stats

| Name | Race | Class |
| ---- | ---- | ----- |
| Neal | Elf | Bard |

## Character Backstory

Neal sings.

## Character Summary

Neal is a performer.
""",
    )

    dot = combined_relationship_dot(build_combined_character_graph([neal]))

    assert '"family_lovington" [label="Lovington", fillcolor="#fef3c7", shape="ellipse"]' in dot
    assert '"neal_lovington" -> "family_lovington" [label="Family"]' in dot


def test_combined_graph_handles_family_attribute_id_collision():
    graph = CharacterGraph(
        schema_version="0.3.0",
        primary_character=PrimaryCharacterRef(id="neal_lovington", name="Neal Lovington", source_file="Neal.md"),
        characters={
            "neal_lovington": CharacterNode(name="Neal Lovington", summary="Neal sings."),
            "family_lovington": CharacterNode(name="Lovington", summary="A related character record."),
        },
        attributes={
            "family_lovington": AttributeNode(value="Lovington", attribute_type="Family", summary="Family name.")
        },
        relationships=[
            RelationshipEdge(
                source="neal_lovington",
                target="family_lovington",
                relationship_type="family",
                relationship_label="Family",
                evidence=["Lovington is inferred as the family name from Neal Lovington."],
            )
        ],
    )

    combined = build_combined_character_graph([graph])

    assert ("neal_lovington", "family_lovington", "family") in {
        (edge.source, edge.target, edge.relationship_type) for edge in combined.edges
    }


def test_combined_graph_deduplicates_same_type_same_name_nodes():
    combined = build_combined_character_graph(
        [],
        lore_relationships=[
            {
                "source_id": "neal_lovington",
                "source_name": "Neal Lovington",
                "source_type": "character",
                "target_id": "mira_vale",
                "target_name": "Mira Vale",
                "target_type": "character",
                "relationship": "Ally",
                "evidence": "Mira Vale helped Neal.",
            },
            {
                "source_id": "jory_ravenmark",
                "source_name": "Jory Ravenmark",
                "source_type": "character",
                "target_id": "mira_vale_from_notes",
                "target_name": "Mira Vale",
                "target_type": "character",
                "relationship": "Ally",
                "evidence": "Mira Vale helped Jory.",
            },
        ],
    )

    mira_nodes = [
        node_id
        for node_id, node in combined.characters.items()
        if node.node_type == "character" and node.name == "Mira Vale"
    ]
    assert mira_nodes == ["mira_vale"]
    assert ("neal_lovington", "mira_vale", "ally") in {
        (edge.source, edge.target, edge.relationship_type) for edge in combined.edges
    }
    assert ("jory_ravenmark", "mira_vale", "ally") in {
        (edge.source, edge.target, edge.relationship_type) for edge in combined.edges
    }
    assert "mira_vale_from_notes" not in combined.characters


def test_combined_graph_deduplicates_edges_after_node_merge():
    combined = build_combined_character_graph(
        [],
        lore_relationships=[
            {
                "source_id": "neal_lovington",
                "source_name": "Neal Lovington",
                "source_type": "character",
                "target_id": "mira_vale",
                "target_name": "Mira Vale",
                "target_type": "character",
                "relationship": "Ally",
                "evidence": "First source.",
            },
            {
                "source_id": "neal_lovington",
                "source_name": "Neal Lovington",
                "source_type": "character",
                "target_id": "mira_vale_duplicate",
                "target_name": "Mira Vale",
                "target_type": "character",
                "relationship": "Ally",
                "evidence": "Second source.",
            },
        ],
    )

    ally_edges = [
        edge
        for edge in combined.edges
        if (edge.source, edge.target, edge.relationship_type) == ("neal_lovington", "mira_vale", "ally")
    ]
    assert len(ally_edges) == 1
    assert ally_edges[0].evidence == ["First source.", "Second source."]


def test_combined_graph_clarifies_same_label_for_different_entity_types():
    combined = build_combined_character_graph(
        [],
        place_sources=[("royal_tittles", "Royal Tittles", "world_building/lore/places/Royal_Tittles.md")],
        lore_relationships=[
            {
                "source_id": "royal_tittles",
                "source_name": "Royal Tittles",
                "source_type": "place",
                "target_id": "royal_tittles_bard",
                "target_name": "Royal Tittles",
                "target_type": "character",
                "relationship": "Named After",
                "evidence": "A bard uses the stage name Royal Tittles.",
            }
        ],
    )

    assert combined.characters["royal_tittles"].name == "Royal Tittles (Place)"
    assert combined.characters["royal_tittles_bard"].name == "Royal Tittles (Character)"
    assert ("royal_tittles", "royal_tittles_bard", "named") in {
        (edge.source, edge.target, edge.relationship_type) for edge in combined.edges
    }


def test_combined_graph_place_sources_override_lore_primary_node_type(tmp_path):
    royal_tittles = graph_from_text(
        tmp_path,
        "Royal_Tittles.md",
        """# Royal Tittles

## Place Summary

Neal Lovington performs at Royal Tittles.
""",
    )

    combined = build_combined_character_graph(
        [royal_tittles],
        place_sources=[("royal_tittles", "Royal Tittles", "world_building/lore/places/Royal_Tittles.md")],
        lore_relationships=[
            {
                "source_id": "royal_tittles",
                "source_name": "Royal Tittles",
                "source_type": "place",
                "target_id": "neal_lovington",
                "target_name": "Neal Lovington",
                "target_type": "character",
                "relationship": "Performs",
                "evidence": "Neal Lovington performs at Royal Tittles.",
            }
        ],
    )

    assert combined.characters["royal_tittles"].node_type == "place"


def test_combined_graph_includes_lore_relationships_without_character_sheets():
    combined = build_combined_character_graph(
        [],
        place_sources=[("royal_tittles", "Royal Tittles", "world_building/lore/places/Royal_Tittles.md")],
        lore_relationships=[
            {
                "source_id": "royal_tittles",
                "source_name": "Royal Tittles",
                "source_type": "place",
                "source_file": "world_building/lore/places/Royal_Tittles.md",
                "target_id": "neal_lovington",
                "target_name": "Neal Lovington",
                "target_type": "character",
                "relationship": "Performs Here",
                "evidence": "Neal Lovington: Performs Here",
            }
        ],
    )

    rows = combined_relationship_rows(combined)

    assert combined.characters["neal_lovington"].node_type == "character"
    assert combined.edges[0].relationship_type == "performs"
    assert rows[0]["Relationship"] == "Performs"
    assert rows[0]["Connection"] == "Neal Lovington"


def test_combined_graph_forbids_self_referencing_lore_edges():
    combined = build_combined_character_graph(
        [],
        lore_relationships=[
            {
                "source_id": "neal_lovington",
                "source_name": "Neal Lovington",
                "source_type": "character",
                "target_id": "neal_lovington",
                "target_name": "Neal Lovington",
                "target_type": "character",
                "relationship": "Self",
                "evidence": "Neal Lovington references himself.",
            }
        ],
    )

    assert combined.edges == []
    assert combined.characters == {}


def test_combined_graph_prunes_disconnected_nodes():
    combined = build_combined_character_graph(
        [],
        place_sources=[("royal_tittles", "Royal Tittles", "world_building/lore/places/Royal_Tittles.md")],
        lore_relationships=[
            {
                "source_id": "neal_lovington",
                "source_name": "Neal Lovington",
                "source_type": "character",
                "target_id": "jory_ravenmark",
                "target_name": "Jory Ravenmark",
                "target_type": "character",
                "relationship": "Ally",
                "evidence": "Jory Ravenmark is Neal Lovington's ally.",
            }
        ],
    )

    assert "royal_tittles" not in combined.characters
    assert set(combined.characters) == {"neal_lovington", "jory_ravenmark"}


def test_append_character_connections_adds_prioritized_table(tmp_path, monkeypatch):
    monkeypatch.setattr("local_chatbot.storage.regenerate_character_graph", lambda character: None)
    path = tmp_path / "Mara_Voss.md"
    path.write_text(
        """# Mara Voss

## Character Stats

| Name | Race |
| ---- | ---- |
| Mara | Elf |

## Character Backstory

Manual backstory.

## Character Summary

Manual summary.
""",
        encoding="utf-8",
    )
    character = Character(name=path.stem, path=path)

    append_character_connections(
        character,
        [
            {"Source": "Self", "Relationship": "Referenced", "Name": "Late Note", "Evidence": "Self evidence"},
            {"Source": "Place", "Relationship": "Place", "Name": "Royal Tittles", "Evidence": "Place evidence"},
        ],
    )

    text = path.read_text(encoding="utf-8")
    profile = read_character_profile(character)
    assert "## Character Connections" in text
    assert text.index("Royal Tittles") < text.index("Late Note")
    assert profile.knowledge_graph_fields


def test_append_character_connections_merges_existing_table_without_losing_rows(tmp_path, monkeypatch):
    monkeypatch.setattr("local_chatbot.storage.regenerate_character_graph", lambda character: None)
    path = tmp_path / "Mara_Voss.md"
    path.write_text(
        """# Mara Voss

## Character Stats

| Name | Race |
| ---- | ---- |
| Mara | Elf |

## Character Backstory

Manual backstory.

## Character Summary

Manual summary.

## Character Connections

| Source | Relationship | Name | Evidence |
| ------ | ------------ | ---- | -------- |
| Self | Referenced | Old Contact | Old evidence |
| Place | Place | Royal Tittles | First evidence |
""",
        encoding="utf-8",
    )
    character = Character(name=path.stem, path=path)

    append_character_connections(
        character,
        [
            {"Source": "Place", "Relationship": "Place", "Name": "Royal Tittles", "Evidence": "Second evidence"},
            {"Source": "Character Sheet", "Relationship": "Ally", "Name": "Jory Ravenmark", "Evidence": "Jory evidence"},
        ],
    )

    text = path.read_text(encoding="utf-8")
    assert "Old Contact" in text
    assert "Jory Ravenmark" in text
    assert "First evidence Second evidence" in text
    assert text.count("Royal Tittles") == 1


def test_append_character_connections_limits_long_table_cell_text(tmp_path, monkeypatch):
    monkeypatch.setattr("local_chatbot.storage.regenerate_character_graph", lambda character: None)
    path = tmp_path / "Mara_Voss.md"
    path.write_text(
        """# Mara Voss

## Character Stats

| Name | Race |
| ---- | ---- |
| Mara | Elf |

## Character Backstory

Manual backstory.

## Character Summary

Manual summary.
""",
        encoding="utf-8",
    )
    character = Character(name=path.stem, path=path)
    long_evidence = "A" * (storage.CHARACTER_CONNECTION_CELL_MAX_LENGTH + 25)

    append_character_connections(
        character,
        [
            {
                "Source": "Character Sheet",
                "Relationship": "Ally",
                "Name": "Jory Ravenmark",
                "Evidence": long_evidence,
            },
        ],
    )

    text = path.read_text(encoding="utf-8")
    evidence_cell = next(line for line in text.splitlines() if "Jory Ravenmark" in line).split("|")[4].strip()
    assert len(evidence_cell) == storage.CHARACTER_CONNECTION_CELL_MAX_LENGTH
    assert evidence_cell.endswith("...")
    assert long_evidence not in text


def test_append_character_connections_summarizes_evidence_with_connection_context(tmp_path, monkeypatch):
    monkeypatch.setattr("local_chatbot.storage.regenerate_character_graph", lambda character: None)
    path = tmp_path / "Mara_Voss.md"
    path.write_text(
        """# Mara Voss

## Character Stats

| Name | Race |
| ---- | ---- |
| Mara | Elf |

## Character Backstory

Manual backstory.

## Character Summary

Manual summary.
""",
        encoding="utf-8",
    )
    character = Character(name=path.stem, path=path)
    filler = " ".join(["The archive shelves were dusty and crowded"] * 8) + "."
    relevant = "Jory Ravenmark is Mara's trusted ally after guarding the west road."

    append_character_connections(
        character,
        [
            {
                "Source": "Character Sheet",
                "Relationship": "Ally",
                "Name": "Jory Ravenmark",
                "Evidence": f"{filler} {relevant}",
            },
        ],
    )

    text = path.read_text(encoding="utf-8")
    evidence_cell = next(line for line in text.splitlines() if "Jory Ravenmark" in line).split("|")[4].strip()
    assert evidence_cell == relevant
    assert "archive shelves" not in evidence_cell
