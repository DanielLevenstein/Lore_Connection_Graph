from pathlib import Path

from character_graph.combined_graph import (
    build_combined_character_graph,
    combined_attribute_rows,
    combined_node_detail_rows,
    default_graphviz_config,
    full_character_connection_graph,
    graph_clarity_metric,
    graph_clarity_rows,
    combined_relationship_dot,
    combined_relationship_rows,
    graph_view_root_nodes,
    other_connection_rows,
    other_connections_graph,
    party_connections_graph,
)
from character_graph.extraction import extract_character_graph
from character_graph.ingest import load_backstory
from character_graph.schema import AttributeNode, CharacterGraph, CharacterNode, PlaceNode, PrimaryCharacterRef, RelationshipEdge
from character_graph.session_entities import derived_lore_entity_relationships, extract_lore_entity_candidates
import local_chatbot.storage as storage
from local_chatbot.storage import Character, append_character_connections, read_character_profile


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def graph_from_text(tmp_path, filename: str, text: str):
    path = tmp_path / filename
    path.write_text(text, encoding="utf-8")
    return extract_character_graph(load_backstory(path, character_id=path.stem))


def fixture_graph(filename: str):
    path = FIXTURES_DIR / "character_sheets" / filename
    return extract_character_graph(load_backstory(path, character_id=path.stem))


def fixture_combined_graph():
    place_path = FIXTURES_DIR / "places" / "Atlantia_Lore.md"
    return build_combined_character_graph(
        [
            fixture_graph("Jory_Ravenmark.md"),
            fixture_graph("Neal_Lovington.md"),
            fixture_graph("Orin_Nightbloom.md"),
        ],
        place_sources=[("atlantia_lore", "Atlantia Lore", str(place_path))],
        lore_relationships=[
            {
                "source_id": "atlantia_lore",
                "source_name": "Atlantia Lore",
                "source_type": "place",
                "source_file": str(place_path),
                "target_id": "jory_ravenmark",
                "target_name": "Jory Ravenmark",
                "target_type": "character",
                "relationship": "Home",
                "evidence": "Atlantia contains the Ravenmark watch tower.",
            }
        ],
    )


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

    assert 'splines="line"' in dot
    assert 'ranksep=1.15, nodesep=0.4' in dot
    assert 'fontcolor="#cbd5e1"' in dot
    assert 'labelfontcolor="#cbd5e1"' in dot
    assert combined.characters["royal_tittles"].node_type == "place"
    assert "Royal Tittles" in dot
    assert 'shape="component"' in dot

    detail_rows = combined_node_detail_rows(combined, "neal_lovington")

    assert {
        "Detail": "Node",
        "Relationship": "",
        "Value": "Neal Lovington",
        "Type": "Character",
        "Evidence": "Source: Neal_Lovington.md",
    } in detail_rows
    assert "/" not in detail_rows[0]["Evidence"]
    assert {
        "Detail": "Outgoing",
        "Relationship": "Performs",
        "Value": "Royal Tittles",
        "Type": "Place",
        "Evidence": "Neal performs at the Royal Tittles Tavern.",
    } in detail_rows


def test_combined_relationship_dot_accepts_graph_text_color(tmp_path):
    neal = graph_from_text(
        tmp_path,
        "Neal_Lovington.md",
        """# Neal Lovington

## Character Backstory

Neal performs at the Royal Tittles Tavern.

## Character Summary

Neal is a performer.
""",
    )

    dot = combined_relationship_dot(build_combined_character_graph([neal]), label_font_color="#f8fafc")

    assert 'fontcolor="#f8fafc"' in dot
    assert 'labelfontcolor="#f8fafc"' in dot


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

    assert combined.characters["family_lovington"].name == "Lovington Family"
    assert combined.characters["family_lovington"].node_type == "family"
    assert ("neal_lovington", "family_lovington", "family") in {
        (edge.source, edge.target, edge.relationship_type) for edge in combined.edges
    }
    assert "race_elf" not in combined.characters
    assert "class_bard" not in combined.characters
    assert "drive_make_a_name" not in combined.characters


def test_fixture_graph_uses_party_column_layout_without_hidden_fixtures():
    combined = fixture_combined_graph()
    party_graph = party_connections_graph(combined, ["jory_ravenmark", "neal_lovington"])

    dot = combined_relationship_dot(
        party_graph,
        focus_node_id="neal_lovington",
        main_character_ids={"jory_ravenmark", "neal_lovington"},
        main_place_ids={"atlantia_lore"},
    )

    column_order = [
        dot.index("cluster_column_0_family_names"),
        dot.index("cluster_column_1_main_characters"),
        dot.index("cluster_column_2_secondary_characters"),
        dot.index("cluster_column_3_places"),
    ]
    assert column_order == sorted(column_order)
    assert 'subgraph "cluster_column_0_family_names"' in dot
    assert '"family_lovington"' in dot
    assert '"family_ravenmark"' in dot
    assert 'subgraph "cluster_column_1_main_characters"' in dot
    assert '"jory_ravenmark"; "neal_lovington"' in dot
    assert 'subgraph "cluster_column_2_secondary_characters"' in dot
    assert '"mrs_nightbloom"' in dot
    assert 'subgraph "cluster_column_3_places"' in dot
    assert "Session Notes" not in dot
    visible_edges = [line for line in dot.splitlines() if "->" in line and "label=" in line]
    assert visible_edges
    assert '"jory_ravenmark" -> "neal_lovington" [label="Client", constraint="false"]' in dot
    assert '"neal_lovington" -> "jory_ravenmark" [label="Client", constraint="false"]' in dot
    cross_column_edges = [
        line
        for line in visible_edges
        if not any(
            same_column_edge in line
            for same_column_edge in [
                '"jory_ravenmark" -> "neal_lovington"',
                '"neal_lovington" -> "jory_ravenmark"',
            ]
        )
    ]
    assert all('constraint="false"' not in line for line in cross_column_edges)
    intra_column_edges = [
        line
        for line in dot.splitlines()
        if "style=invis" in line and "weight=50" in line
    ]
    assert intra_column_edges
    assert all('constraint="false"' in line for line in intra_column_edges)


def test_party_column_layout_orders_connections_by_mention_count():
    relationships = [
        {
            "source_id": "neal_lovington",
            "source_name": "Neal Lovington",
            "source_type": "character",
            "source_file": "tests/fixtures/character_sheets/Neal_Lovington.md",
            "target_id": "jory_ravenmark",
            "target_name": "Jory Ravenmark",
            "target_type": "character",
            "relationship": "Client",
            "evidence": "Jory visited Neal.",
        }
    ]
    relationships.extend(
        {
            "source_id": "neal_lovington",
            "source_name": "Neal Lovington",
            "source_type": "character",
            "source_file": "tests/fixtures/character_sheets/Neal_Lovington.md",
            "target_id": "mrs_nightbloom",
            "target_name": "Mrs Nightbloom",
            "target_type": "character",
            "relationship": "Enemy",
            "evidence": f"Mrs Nightbloom mention {index}.",
        }
        for index in range(3)
    )
    relationships.extend(
        [
            {
                "source_id": "neal_lovington",
                "source_name": "Neal Lovington",
                "source_type": "character",
                "source_file": "tests/fixtures/character_sheets/Neal_Lovington.md",
                "target_id": "orin_nightbloom",
                "target_name": "Orin Nightbloom",
                "target_type": "character",
                "relationship": "Client",
                "evidence": "Orin visited Neal once.",
            },
            {
                "source_id": "jory_ravenmark",
                "source_name": "Jory Ravenmark",
                "source_type": "character",
                "source_file": "tests/fixtures/character_sheets/Jory_Ravenmark.md",
                "target_id": "lantern_house",
                "target_name": "Lantern House",
                "target_type": "place",
                "relationship": "Visited",
                "evidence": "Jory visited the Lantern House.",
            },
            {
                "source_id": "neal_lovington",
                "source_name": "Neal Lovington",
                "source_type": "character",
                "source_file": "tests/fixtures/character_sheets/Neal_Lovington.md",
                "target_id": "ashton",
                "target_name": "Ashton",
                "target_type": "place",
                "relationship": "Home",
                "evidence": "Neal mentioned Ashton.",
            },
        ]
    )
    combined = build_combined_character_graph([], lore_relationships=relationships)
    party_graph = party_connections_graph(combined, ["jory_ravenmark", "neal_lovington"])

    dot = combined_relationship_dot(
        party_graph,
        main_character_ids={"jory_ravenmark", "neal_lovington"},
    )

    main_column = dot[
        dot.index('subgraph "cluster_column_1_main_characters"') :
        dot.index('subgraph "cluster_column_2_secondary_characters"')
    ]
    assert '"jory_ravenmark"' in main_column
    assert '"neal_lovington"' in main_column
    secondary_column = dot[
        dot.index('subgraph "cluster_column_2_secondary_characters"') :
        dot.index('subgraph "cluster_column_3_places"')
    ]
    assert secondary_column.index('"mrs_nightbloom"') < secondary_column.index('"orin_nightbloom"')
    assert secondary_column.index('"ashton"') < secondary_column.index('"lantern_house"')
    place_cluster_line = next(line for line in dot.splitlines() if 'cluster_column_3_places' in line)
    assert '"ashton"' not in place_cluster_line
    assert '"lantern_house"' not in place_cluster_line


def test_other_connection_rows_split_repeated_evidence_into_separate_rows():
    relationships = [
        {
            "source_id": "neal_lovington",
            "source_name": "Neal Lovington",
            "source_type": "character",
            "source_file": "tests/fixtures/character_sheets/Neal_Lovington.md",
            "target_id": "mrs_nightbloom",
            "target_name": "Mrs Nightbloom",
            "target_type": "character",
            "relationship": "Enemy",
            "evidence": f"Mrs Nightbloom mention {index}.",
        }
        for index in range(3)
    ]
    combined = build_combined_character_graph([], lore_relationships=relationships)

    rows = other_connection_rows(combined, "neal_lovington")

    assert rows == [
        {"Connection": "Mrs Nightbloom", "Type": "Character", "Evidence": "Mrs Nightbloom mention 0."},
        {"Connection": "Mrs Nightbloom", "Type": "Character", "Evidence": "Mrs Nightbloom mention 1."},
        {"Connection": "Mrs Nightbloom", "Type": "Character", "Evidence": "Mrs Nightbloom mention 2."},
    ]


def test_fixture_graph_handles_missing_family_names_without_toggle():
    combined = fixture_combined_graph()

    focused = other_connections_graph(combined, "atlantia_lore")
    dot = combined_relationship_dot(
        focused,
        focus_node_id="atlantia_lore",
        main_character_ids={"jory_ravenmark", "neal_lovington"},
        main_place_ids={"atlantia_lore"},
    )

    assert all(node.node_type != "family" for node in focused.characters.values())
    assert 'subgraph "cluster_column_0_family_names" { rank=same; style=invis; "graph_column_0"; }' in dot
    assert "Atlantia_Lore.md" not in dot
    assert combined_node_detail_rows(combined, "atlantia_lore")[0]["Evidence"] == "Source: Atlantia_Lore.md"


def test_combined_graph_limits_session_note_graph_to_source_and_places():
    graph = CharacterGraph(
        schema_version="0.2.0",
        primary_character=PrimaryCharacterRef(
            id="this",
            name="This",
            source_file="world_building/import/Session_Notes.txt",
        ),
        characters={
            "this": CharacterNode(name="This"),
            "there": CharacterNode(name="There"),
            "did": CharacterNode(name="Did"),
            "you": CharacterNode(name="You"),
        },
        attributes={
            "family_notes": AttributeNode(value="Notes", attribute_type="Family"),
        },
        places={
            "pixie_kingdom": PlaceNode(name="Pixie Kingdom", place_type="Kingdom"),
            "forest": PlaceNode(name="Forest", place_type="Forest"),
        },
        relationships=[
            RelationshipEdge(
                source="this",
                target="there",
                relationship_type="ally",
                relationship_label="Ally",
                evidence=["There was an ally-shaped false positive."],
            ),
            RelationshipEdge(
                source="this",
                target="family_notes",
                relationship_type="family",
                relationship_label="Family",
                evidence=["Notes is inferred from the session note title."],
            ),
            RelationshipEdge(
                source="this",
                target="pixie_kingdom",
                relationship_type="place",
                relationship_label="Place",
                evidence=["The party traveled to the Pixie Kingdom."],
            ),
            RelationshipEdge(
                source="this",
                target="forest",
                relationship_type="place",
                relationship_label="Place",
                evidence=["The party moved through the forest."],
            ),
        ],
    )

    combined = build_combined_character_graph([graph])

    assert set(combined.characters) == {"this", "pixie_kingdom", "forest"}
    assert combined.characters["this"].name == "Session Notes"
    assert [(edge.source, edge.relationship_label, edge.target) for edge in combined.edges] == [
        ("this", "Place", "pixie_kingdom"),
        ("this", "Place", "forest"),
    ]


def test_session_note_entity_extraction_promotes_likely_characters_and_places():
    text = """# Session Notes

Vivit and Morningstar met John Doctor in Mentha. Vivit warned Typhon about John Doctor.
Morningstar and Typhon regrouped with Vivit. Typhon asked Morningstar to wait for Mog.
Mog helped Dizlevad cross the washed-out bridge near Craigwood. Mog and Dizlevad made camp. Dizlevad thanked Mog.
The Party visited the Pixie Kingdom.
There were fires in the town. Did the town recover?
"""

    relationships = derived_lore_entity_relationships(
        source_id="session_notes",
        source_name="Session Notes",
        source_type="character",
        source_file="world_building/lore/session_notes/Session_Notes.md",
        text=text,
    )
    combined = build_combined_character_graph([], lore_relationships=relationships)

    assert {
        "vivit",
        "morningstar",
        "johndoctor",
        "mog",
        "dizlevad",
        "pixiekingdom",
        "mentha",
        "craigwood",
    } <= set(combined.characters)
    assert "there" not in combined.characters
    assert "did" not in combined.characters
    assert len(combined.characters) <= 28


def test_graph_view_roots_are_only_main_characters_and_places():
    relationships = [
        {
            "source_id": "session_notes",
            "source_name": "Session Notes",
            "source_type": "character",
            "source_file": "world_building/lore/session_notes/Session_Notes.md",
            "target_id": "dizlevad",
            "target_name": "Dizlevad",
            "target_type": "character",
            "relationship": "Mentioned",
            "evidence": "Dizlevad traveled with Mog near Craigwood.",
        },
        {
            "source_id": "session_notes",
            "source_name": "Session Notes",
            "source_type": "character",
            "source_file": "world_building/lore/session_notes/Session_Notes.md",
            "target_id": "mog",
            "target_name": "Mog",
            "target_type": "character",
            "relationship": "Mentioned",
            "evidence": "Dizlevad traveled with Mog near Craigwood.",
        },
        {
            "source_id": "session_notes",
            "source_name": "Session Notes",
            "source_type": "character",
            "source_file": "world_building/lore/session_notes/Session_Notes.md",
            "target_id": "craigwood",
            "target_name": "Craigwood",
            "target_type": "place",
            "relationship": "Location",
            "evidence": "Dizlevad traveled with Mog near Craigwood.",
        },
    ]
    combined = build_combined_character_graph([], lore_relationships=relationships)

    roots = graph_view_root_nodes(combined, ["Dizlevad"], ["Craigwood"])

    assert [(node.name, node.node_type) for node in roots] == [
        ("Dizlevad", "character"),
        ("Craigwood", "place"),
    ]
    assert "Session Notes" not in {node.name for node in roots}
    assert "Mog" not in {node.name for node in roots}


def test_graph_view_roots_do_not_fallback_to_session_notes():
    relationships = [
        {
            "source_id": "session_notes",
            "source_name": "Session Notes",
            "source_type": "character",
            "source_file": "world_building/lore/session_notes/Session_Notes.md",
            "target_id": "mog",
            "target_name": "Mog",
            "target_type": "character",
            "relationship": "Mentioned",
            "evidence": "Mog appeared in the notes.",
        }
    ]
    combined = build_combined_character_graph([], lore_relationships=relationships)

    assert graph_view_root_nodes(combined, [], []) == []


def test_full_character_connection_graph_excludes_session_notes_node():
    relationships = [
        {
            "source_id": "session_notes",
            "source_name": "Session Notes",
            "source_type": "character",
            "source_file": "world_building/lore/session_notes/Session_Notes.md",
            "target_id": "jory_ravenmark",
            "target_name": "Jory Ravenmark",
            "target_type": "character",
            "relationship": "Mentioned",
            "evidence": "Session Notes mentioned Jory Ravenmark.",
        },
        {
            "source_id": "jory_ravenmark",
            "source_name": "Jory Ravenmark",
            "source_type": "character",
            "source_file": "tests/fixtures/character_sheets/Jory_Ravenmark.md",
            "target_id": "neal_lovington",
            "target_name": "Neal Lovington",
            "target_type": "character",
            "relationship": "Client",
            "evidence": "Jory Ravenmark knows Neal Lovington.",
        },
    ]
    combined = build_combined_character_graph([], lore_relationships=relationships)

    full_graph = full_character_connection_graph(combined)
    dot = combined_relationship_dot(full_graph)

    assert "session_notes" not in full_graph.characters
    assert "Session Notes" not in dot
    assert set(full_graph.characters) == {"jory_ravenmark", "neal_lovington"}
    assert [(edge.source, edge.target) for edge in full_graph.edges] == [("jory_ravenmark", "neal_lovington")]


def test_full_character_connection_graph_places_source_document_in_family_column():
    graph = CharacterGraph(
        schema_version="0.3.0",
        primary_character=PrimaryCharacterRef(
            id="family_tree",
            name="Family Tree",
            source_file="world_building/lore/session_notes/Family_Tree.md",
        ),
        characters={"family_tree": CharacterNode(name="Family Tree")},
        places={"atlantia": PlaceNode(name="Atlantia", place_type="City")},
        relationships=[
            RelationshipEdge(
                source="family_tree",
                target="atlantia",
                relationship_type="place",
                relationship_label="Place",
                evidence=["Family Tree notes mention Atlantia."],
            )
        ],
    )
    combined = build_combined_character_graph(
        [graph],
        lore_relationships=[
            {
                "source_id": "family_tree",
                "source_name": "Family Tree",
                "source_type": "character",
                "source_file": "world_building/lore/session_notes/Family_Tree.md",
                "target_id": "neal_lovington",
                "target_name": "Neal Lovington",
                "target_type": "character",
                "relationship": "Mentioned",
                "evidence": "Family Tree notes mention Neal Lovington.",
            }
        ],
    )

    full_graph = full_character_connection_graph(combined)
    focused_graph = other_connections_graph(combined, "neal_lovington")
    dot = combined_relationship_dot(full_graph)
    family_column = dot[
        dot.index('subgraph "cluster_column_0_family_names"') :
        dot.index('subgraph "cluster_column_1_main_characters"')
    ]

    assert combined.characters["family_tree"].node_type == "source_document"
    assert "family_tree" in full_graph.characters
    assert '"family_tree" [label="Family Tree", fillcolor="#fde68a"' in dot
    assert 'shape="folder", width=1.65, height=0.7, margin="0.12,0.06"' in dot
    assert '"family_tree"' in family_column
    assert "family_tree" in focused_graph.characters
    assert "Family Tree" in combined_relationship_dot(focused_graph, "neal_lovington")


def test_family_tree_source_document_links_through_character_family_nodes():
    family_tree_text = """# Family Tree

## The Nighbloom Family

Mrs. Judeth Nightbloom is a teacher at Sunstone Mage College.

## The Ravenmark Family

Jory still believes her father was taken by a sea monster.

## The Lovington Family

Neal Lovington came from a town far away.
"""
    relationships = derived_lore_entity_relationships(
        source_id="family_tree",
        source_name="Family Tree",
        source_type="character",
        source_file="world_building/lore/session_notes/Family_Tree.md",
        text=family_tree_text,
        known_character_names=["Jory Ravenmark", "Neal Lovington", "Orin Nightbloom"],
        known_place_names=[],
    )
    combined = build_combined_character_graph(
        [
            fixture_graph("Jory_Ravenmark.md"),
            fixture_graph("Neal_Lovington.md"),
            fixture_graph("Orin_Nightbloom.md"),
        ],
        lore_relationships=relationships,
    )

    assert ("family_tree", "family_nightbloom", "family") in {
        (edge.source, edge.target, edge.relationship_type) for edge in combined.edges
    }

    expected_evidence = {
        "jory_ravenmark": "The Ravenmark Family",
        "neal_lovington": "The Lovington Family",
        "orin_nightbloom": "The Nighbloom Family",
    }
    for node_id, evidence in expected_evidence.items():
        focused_graph = other_connections_graph(combined, node_id)
        rows = other_connection_rows(combined, node_id)

        assert "family_tree" in focused_graph.characters
        assert (
            node_id,
            "Family",
            "family_tree",
        ) in [(edge.source, edge.relationship_label, edge.target) for edge in focused_graph.edges]
        assert {
            "Connection": "Family Tree",
            "Type": "Source_Document",
            "Evidence": evidence,
        } in rows


def test_session_note_entity_extraction_prioritizes_known_character_names():
    text = "Jory Ravenmark joined Vivit. Vivit and Mog later met Vivit again near the Feywild."

    candidates = extract_lore_entity_candidates(
        text,
        known_character_names=["Jory Ravenmark"],
        known_place_names=["Feywild"],
    )
    character_names = [candidate.name for candidate in candidates if candidate.entity_type == "character"]
    place_names = [candidate.name for candidate in candidates if candidate.entity_type == "place"]

    assert "Jory Ravenmark" in character_names
    assert "Vivit" in character_names
    assert "Feywild" in place_names


def test_session_note_entity_extraction_promotes_group_names_to_family_column():
    text = "The party learned about the Cult of Ignis. Later the Ignis cult attacked the carnival."
    relationships = derived_lore_entity_relationships(
        source_id="session_notes",
        source_name="Session Notes",
        source_type="character",
        source_file="world_building/lore/session_notes/Session_Notes.md",
        text=text,
    )
    combined = build_combined_character_graph([], lore_relationships=relationships)
    full_graph = full_character_connection_graph(combined)
    dot = combined_relationship_dot(full_graph)
    family_column = dot[
        dot.index('subgraph "cluster_column_0_family_names"') :
        dot.index('subgraph "cluster_column_1_main_characters"')
    ]

    assert combined.characters["igniscult"].name == "Ignis Cult"
    assert combined.characters["igniscult"].node_type == "group"
    assert ("session_notes", "igniscult", "mentioned") in {
        (edge.source, edge.target, edge.relationship_type) for edge in combined.edges
    }
    assert '"igniscult" [label="Ignis Cult", fillcolor="#e9d5ff"' in dot
    assert 'shape="trapezium"' in dot
    assert '"igniscult"' in family_column


def test_combined_graph_uses_vertical_layout_for_broad_session_note_hubs():
    relationships = [
        {
            "source_id": "session_notes",
            "source_name": "Session Notes",
            "source_type": "character",
            "source_file": "world_building/lore/session_notes/Session_Notes.md",
            "target_id": f"character_{index}",
            "target_name": f"Character {index}",
            "target_type": "character",
            "relationship": "Mentioned",
            "evidence": f"Character {index} appeared in the session notes.",
        }
        for index in range(22)
    ]

    dot = combined_relationship_dot(build_combined_character_graph([], lore_relationships=relationships))

    assert "rankdir=TB" in dot
    assert 'constraint="false"' in dot
    assert "style=invis" in dot


def test_other_connections_graph_summarizes_session_note_relationships():
    relationships = [
        {
            "source_id": "session_notes",
            "source_name": "Session Notes",
            "source_type": "character",
            "source_file": "world_building/lore/session_notes/Session_Notes.md",
            "target_id": f"character_{index}",
            "target_name": f"Character {index}",
            "target_type": "character",
            "relationship": "Mentioned",
            "evidence": (
                f"Character {index} appeared in the session notes."
                if index != 4
                else "Another figure appeared elsewhere."
            ),
        }
        for index in range(14)
    ]
    relationships.extend(
        [
            {
                "source_id": "character_3",
                "source_name": "Character 3",
                "source_type": "character",
                "source_file": "world_building/lore/session_notes/Session_Notes.md",
                "target_id": "pixie_kingdom",
                "target_name": "Pixie Kingdom",
                "target_type": "place",
                "relationship": "Location",
                "evidence": "Character 3 visited the Pixie Kingdom.",
            },
            {
                "source_id": "character_3",
                "source_name": "Character 3",
                "source_type": "character",
                "source_file": "world_building/lore/session_notes/Session_Notes.md",
                "target_id": "mentor",
                "target_name": "Mentor",
                "target_type": "character",
                "relationship": "Mentioned",
                "evidence": "Character 3 met Mentor.",
            },
        ]
    )
    combined = build_combined_character_graph([], lore_relationships=relationships)

    focused = other_connections_graph(combined, "character_3")
    rows = other_connection_rows(combined, "character_3")

    assert set(focused.characters) == {"character_3", "mentor", "pixie_kingdom"}
    assert [(edge.source, edge.relationship_label, edge.target) for edge in focused.edges] == [
        ("character_3", "Location", "pixie_kingdom"),
        ("character_3", "Mentioned", "mentor"),
    ]
    assert "session_notes" not in focused.characters
    assert "Session Notes" not in combined_relationship_dot(focused, "character_3")
    assert "Other Connections" not in combined_relationship_dot(focused, "character_3")
    assert "Character 4" not in {row["Connection"] for row in rows}
    assert {"Connection": "Pixie Kingdom", "Type": "Place", "Evidence": "Character 3 visited the Pixie Kingdom."} in rows
    assert {"Connection": "Mentor", "Type": "Character", "Evidence": "Character 3 met Mentor."} in rows
    assert graph_clarity_metric(focused).score > graph_clarity_metric(combined).score
    assert graph_clarity_rows(combined, focused)[0]["View"] == "Before Selection"
    assert graph_clarity_rows(combined, focused)[1]["View"] == "Selected View"


def test_other_connections_graph_keeps_late_session_note_co_mentions():
    early_typhon_mentions = " ".join(f"Typhon handled trouble number {index}." for index in range(12))
    text = f"""# Session Notes

{early_typhon_mentions}
As the rain became heavier the party stopped with the efforts of Mog and Dizlevad.
The combination works of Mog and Dizlevad collecting trees and other fallen debris, and Morningstar using plant growth.
With Dizelvad communicating they are there to help and the devistating spell that Typhin cast, the party and the satyr mounted centaurs take down the cultists with ease.
The combined work of Flicker healing and Dizlevad cleaning the wound saves the wyrmling as Typhin and Morningstar talk to it.
Mog and Flicker went to the Feasting Orchard while Dizelvad and Typhen went to the swan boat rides.
"""
    relationships = derived_lore_entity_relationships(
        source_id="session_notes",
        source_name="Session Notes",
        source_type="character",
        source_file="world_building/lore/session_notes/Session_Notes.md",
        text=text,
        known_character_names=["Dizlevad", "Mog", "Typhon", "Flicker"],
    )
    combined = build_combined_character_graph([], lore_relationships=relationships)

    focused = other_connections_graph(combined, "dizlevad")
    rows = other_connection_rows(combined, "dizlevad")
    connections = {row["Connection"] for row in rows}

    assert {"Mog", "Typhon", "Flicker", "Morningstar", "Feasting Orchard"} <= connections
    assert len(rows) >= 5
    assert "session_notes" not in focused.characters
    assert "Session Notes" not in combined_relationship_dot(focused, "dizlevad")
    assert "Other Connections" not in combined_relationship_dot(focused, "dizlevad")
    assert any("Typhin" in row["Evidence"] or "Typhen" in row["Evidence"] for row in rows if row["Connection"] == "Typhon")


def test_session_note_entity_evidence_does_not_match_honorific_only_aliases():
    text = """John Doctor patched up the party. Mr Light thanked the party.
Upon arrival she would tell Dizelvad about how she became separated from Mr Cloppington.
Dizlevad later spoke with Mog.
"""
    relationships = derived_lore_entity_relationships(
        source_id="session_notes",
        source_name="Session Notes",
        source_type="character",
        source_file="world_building/lore/session_notes/Session_Notes.md",
        text=text,
        known_character_names=["Dizlevad", "Mog"],
    )
    combined = build_combined_character_graph([], lore_relationships=relationships)
    rows = other_connection_rows(combined, "dizlevad")
    connections = {row["Connection"] for row in rows}

    assert "Mog" in connections
    assert "Mr Light" not in connections
    assert "John Doctor" not in connections


def test_other_connections_graph_limits_broad_session_note_connections():
    relationships = [
        {
            "source_id": "session_notes",
            "source_name": "Session Notes",
            "source_type": "character",
            "source_file": "world_building/lore/session_notes/Session_Notes.md",
            "target_id": "typhon",
            "target_name": "Typhon",
            "target_type": "character",
            "relationship": "Mentioned",
            "evidence": "Typhon crossed paths with several people at the carnival.",
        }
    ]
    for index in range(12):
        relationships.append(
            {
                "source_id": "session_notes",
                "source_name": "Session Notes",
                "source_type": "character",
                "source_file": "world_building/lore/session_notes/Session_Notes.md",
                "target_id": f"connection_{index}",
                "target_name": f"Connection {index}",
                "target_type": "character",
                "relationship": "Mentioned",
                "evidence": f"Typhon crossed paths with Connection {index} at the carnival.",
            }
        )
    combined = build_combined_character_graph([], lore_relationships=relationships)

    focused = other_connections_graph(combined, "typhon")
    rows = other_connection_rows(combined, "typhon")

    assert len(focused.edges) == 6
    assert len(rows) == 6


def test_combined_relationship_dot_highlights_focused_node():
    relationships = [
        {
            "source_id": "session_notes",
            "source_name": "Session Notes",
            "source_type": "character",
            "source_file": "world_building/lore/session_notes/Session_Notes.md",
            "target_id": "vivit",
            "target_name": "Vivit",
            "target_type": "character",
            "relationship": "Mentioned",
            "evidence": "Vivit appeared in the session notes.",
        }
    ]
    dot = combined_relationship_dot(
        build_combined_character_graph([], lore_relationships=relationships),
        focus_node_id="vivit",
    )

    assert '"vivit" [label="Vivit", fillcolor="#dbeafe", color="#ef4444", penwidth="2.5"' in dot


def test_combined_relationship_dot_shows_most_prominent_connection_label():
    relationships = [
        {
            "source_id": "neal_lovington",
            "source_name": "Neal Lovington",
            "source_type": "character",
            "target_id": "jory_ravenmark",
            "target_name": "Jory Ravenmark",
            "target_type": "character",
            "relationship": "Mentioned",
            "evidence": "Neal mentioned Jory.",
        },
        {
            "source_id": "neal_lovington",
            "source_name": "Neal Lovington",
            "source_type": "character",
            "target_id": "jory_ravenmark",
            "target_name": "Jory Ravenmark",
            "target_type": "character",
            "relationship": "Enemy",
            "evidence": "Neal fought Jory.",
        },
        {
            "source_id": "neal_lovington",
            "source_name": "Neal Lovington",
            "source_type": "character",
            "target_id": "jory_ravenmark",
            "target_name": "Jory Ravenmark",
            "target_type": "character",
            "relationship": "Enemy",
            "evidence": "Neal distrusted Jory.",
        },
    ]

    dot = combined_relationship_dot(build_combined_character_graph([], lore_relationships=relationships))

    assert dot.count('"neal_lovington" -> "jory_ravenmark"') == 1
    assert '[label="Enemy"' in dot
    assert '[label="Mentioned"' not in dot


def test_combined_relationship_dot_displays_rivals_label():
    combined = build_combined_character_graph(
        [],
        lore_relationships=[
            {
                "source_id": "arlen_voss",
                "source_name": "Arlen Voss",
                "source_type": "character",
                "target_id": "torvak",
                "target_name": "Torvak",
                "target_type": "character",
                "relationship": "Rival",
                "evidence": "Torvak is Arlen's rival.",
            }
        ],
    )

    dot = combined_relationship_dot(combined)

    assert '"arlen_voss" -> "torvak" [label="Rivals"]' in dot


def test_combined_relationship_dot_stacks_focused_targets_in_same_column():
    combined = build_combined_character_graph(
        [],
        lore_relationships=[
            {
                "source_id": "orin_nightbloom",
                "source_name": "Orin Nightbloom",
                "source_type": "character",
                "target_id": "family_tree",
                "target_name": "Family Tree",
                "target_type": "source_document",
                "relationship": "Family",
                "evidence": "The Nighbloom Family",
            },
            {
                "source_id": "orin_nightbloom",
                "source_name": "Orin Nightbloom",
                "source_type": "character",
                "target_id": "mrs_nightbloom",
                "target_name": "Mrs Nightbloom",
                "target_type": "character",
                "relationship": "Family",
                "evidence": "Orin Nightbloom's mother was Mrs Nightbloom.",
            },
            {
                "source_id": "orin_nightbloom",
                "source_name": "Orin Nightbloom",
                "source_type": "character",
                "target_id": "sunstone_mage_college",
                "target_name": "Sunstone Mage College",
                "target_type": "place",
                "relationship": "Place",
                "evidence": "Orin studied at Sunstone Mage College.",
            },
        ],
    )

    dot = combined_relationship_dot(combined, "orin_nightbloom")
    main_column = dot[
        dot.index('subgraph "cluster_column_1_main_characters"') :
        dot.index('subgraph "cluster_column_2_secondary_characters"')
    ]
    secondary_column = dot[
        dot.index('subgraph "cluster_column_2_secondary_characters"') :
        dot.index('subgraph "cluster_column_3_places"')
    ]
    place_cluster_line = next(line for line in dot.splitlines() if 'cluster_column_3_places' in line)

    assert '"orin_nightbloom"' in main_column
    assert '"orin_nightbloom"' not in secondary_column
    assert '"mrs_nightbloom"' in secondary_column
    assert '"sunstone_mage_college"' in secondary_column
    assert '"sunstone_mage_college"' not in place_cluster_line
    assert '"orin_nightbloom" -> "family_tree" [label="Family"' in dot
    assert '"orin_nightbloom" -> "mrs_nightbloom" [label="Family"' in dot
    assert '"orin_nightbloom" -> "sunstone_mage_college" [label="Place"' in dot
    assert "taillabel=" not in dot


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

    assert '"family_lovington" [label="Lovington Family", fillcolor="#fef3c7"' in dot
    assert 'shape="ellipse", width=1.9, height=0.8, margin="0.14,0.06"' in dot
    assert "regular=true" not in dot
    assert '"neal_lovington" -> "family_lovington" [label="Family"]' in dot
    assert "headlabel=" not in dot


def test_combined_relationship_dot_uses_graphviz_node_type_overrides(tmp_path):
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
    config = default_graphviz_config()
    config["node_type_overrides"]["family"]["shape"] = "folder"
    config["node_type_overrides"]["family"]["fillcolor"] = "#fff7ed"

    dot = combined_relationship_dot(
        build_combined_character_graph([neal]),
        graphviz_config=config,
    )

    assert '"family_lovington" [label="Lovington Family", fillcolor="#fff7ed"' in dot
    assert 'shape="folder", width=1.9, height=0.8, margin="0.14,0.06"' in dot


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


def test_combined_relationship_rows_split_edge_evidence_into_rows():
    combined = build_combined_character_graph(
        [],
        lore_relationships=[
            {
                "source_id": "neal_lovington",
                "source_name": "Neal Lovington",
                "source_type": "character",
                "target_id": "jory_ravenmark",
                "target_name": "Jory Ravenmark",
                "target_type": "character",
                "relationship": "Ally",
                "evidence": "Neal helped Jory.",
            },
            {
                "source_id": "neal_lovington",
                "source_name": "Neal Lovington",
                "source_type": "character",
                "target_id": "jory_ravenmark",
                "target_name": "Jory Ravenmark",
                "target_type": "character",
                "relationship": "Ally",
                "evidence": "Jory trusted Neal.",
            },
        ],
    )

    rows = combined_relationship_rows(combined)

    assert [row["Evidence"] for row in rows] == ["Neal helped Jory.", "Jory trusted Neal."]


def test_combined_graph_evidence_rows_strip_markdown_bullets():
    combined = build_combined_character_graph(
        [],
        lore_relationships=[
            {
                "source_id": "neal_lovington",
                "source_name": "Neal Lovington",
                "source_type": "character",
                "target_id": "jory_ravenmark",
                "target_name": "Jory Ravenmark",
                "target_type": "character",
                "relationship": "Ally",
                "evidence": "- Neal helped Jory.",
            },
            {
                "source_id": "neal_lovington",
                "source_name": "Neal Lovington",
                "source_type": "character",
                "target_id": "atlantia",
                "target_name": "Atlantia",
                "target_type": "place",
                "relationship": "Location",
                "evidence": "1. Neal visited Atlantia.",
            },
        ],
    )

    relationship_rows = combined_relationship_rows(combined)
    other_rows = other_connection_rows(combined, "neal_lovington")

    assert {row["Evidence"] for row in relationship_rows} == {
        "Neal helped Jory.",
        "Neal visited Atlantia.",
    }
    assert {row["Evidence"] for row in other_rows} == {
        "Neal helped Jory.",
        "Neal visited Atlantia.",
    }


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
