from character_graph.combined_graph import (
    build_combined_character_graph,
    combined_relationship_dot,
    combined_relationship_rows,
)
from character_graph.extraction import extract_character_graph
from character_graph.ingest import load_backstory
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
        place_sources=[("royal_tittles", "Royal Tittles", "docs/lore/places/Royal_Tittles.md")],
    )

    dot = combined_relationship_dot(combined)

    assert combined.characters["royal_tittles"].node_type == "place"
    assert "Royal Tittles" in dot
    assert 'shape="component"' in dot


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
        place_sources=[("royal_tittles", "Royal Tittles", "docs/lore/places/Royal_Tittles.md")],
    )

    assert combined.characters["royal_tittles"].node_type == "place"


def test_combined_graph_includes_lore_relationships_without_character_sheets():
    combined = build_combined_character_graph(
        [],
        place_sources=[("royal_tittles", "Royal Tittles", "docs/lore/places/Royal_Tittles.md")],
        lore_relationships=[
            {
                "source_id": "royal_tittles",
                "source_name": "Royal Tittles",
                "source_type": "place",
                "source_file": "docs/lore/places/Royal_Tittles.md",
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
