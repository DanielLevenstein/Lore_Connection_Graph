from character_graph.combined_graph import (
    build_combined_character_graph,
    combined_relationship_dot,
    combined_relationship_rows,
)
from character_graph.extraction import extract_character_graph
from character_graph.ingest import load_backstory
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
