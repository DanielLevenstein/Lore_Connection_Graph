from character_graph.combined_graph import (
    CombinedCharacterGraph,
    CombinedCharacterNode,
    CombinedRelationshipEdge,
    combined_relationship_dot,
)
import json
from pathlib import Path
from graphviz_rendering import (
    PARTY_VIEW_TAB,
    PLACE_LORE_TAB,
    PLACES_GRAPH_TAB,
    SINGLE_CHARACTER_TAB,
    graph_without_lore_source_knots,
    graph_tab_names,
    place_lore_connection_rows,
    place_lore_graph,
    session_note_graph,
    session_note_lore_graph,
)


GRAPH_VIEW_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "graph_views"


def test_graph_view_fixtures_cover_current_information_views():
    fixtures = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(GRAPH_VIEW_FIXTURES_DIR.glob("*.json"))
    ]

    assert {
        (fixture["graph_family"], fixture["view"], fixture["top_level_tab"], fixture["screenshot"])
        for fixture in fixtures
    } == {
        ("Characters Graph", "Single Character", "Characters", "Characters_Graph_Single_Character.png"),
        ("Characters Graph", "Party View", "Characters", "Characters_Graph_Party_View.png"),
        ("Places Graph", "Place Lore", "Places", "Places_Graph_Place_Lore.png"),
        ("Places Graph", "Party View", "Places", "Places_Graph_Party_View.png"),
        ("Session Notes Graph", "Place Lore", "Session Notes", "Session_Notes_Graph_Place_Lore.png"),
        ("Session Notes Graph", "Party View", "Session Notes", "Session_Notes_Graph_Party_View.png"),
    }


def test_graph_tabs_follow_active_main_tab():
    assert graph_tab_names("Characters") == [SINGLE_CHARACTER_TAB, PARTY_VIEW_TAB]
    assert graph_tab_names("Places") == [PLACES_GRAPH_TAB, PARTY_VIEW_TAB]
    assert graph_tab_names("Session Notes") == [PLACE_LORE_TAB, PARTY_VIEW_TAB]


def test_place_lore_graph_keeps_source_place_and_character_connections(tmp_path):
    place_lore_path = tmp_path / "Atlantia_Lore.md"
    place_lore_path.write_text(
        "\n".join(
            [
                "# Atlantia Lore",
                "Atlantia is home to Jory Ravenmark.",
                "## Sunstone Mage College",
                "Orin Nightbloom studied at Sunstone Mage College.",
                "### Faculty",
                "Mrs Nightbloom keeps old records here.",
                "#### Ignored Detail",
                "This deeper heading is not shown in the place graph.",
                "Stone and Students are common words here.",
            ]
        ),
        encoding="utf-8",
    )
    family_tree_path = tmp_path / "Family_Tree.md"
    family_tree_path.write_text(
        "\n".join(
            [
                "# Family Tree",
                "Atlantia is listed beside Mrs Nightbloom.",
            ]
        ),
        encoding="utf-8",
    )
    graph = CombinedCharacterGraph(
        characters={
            "source_document__atlantia_lore": CombinedCharacterNode(
                id="source_document__atlantia_lore",
                name="Atlantia Lore",
                source_file=str(place_lore_path),
                node_type="source_document",
            ),
            "atlantia": CombinedCharacterNode(
                id="atlantia",
                name="Atlantia",
                source_file=str(place_lore_path),
                node_type="place",
            ),
            "jory_ravenmark": CombinedCharacterNode(
                id="jory_ravenmark",
                name="Jory Ravenmark",
                source_file="world_building/lore/character_sheets/Jory_Ravenmark.md",
                node_type="character",
            ),
            "orin_nightbloom": CombinedCharacterNode(
                id="orin_nightbloom",
                name="Orin Nightbloom",
                source_file="world_building/lore/character_sheets/Orin_Nightbloom.md",
                node_type="character",
            ),
            "sunstone_mage_college": CombinedCharacterNode(
                id="sunstone_mage_college",
                name="Sunstone Mage College",
                source_file=str(place_lore_path),
                node_type="place",
            ),
            "ignis_cult": CombinedCharacterNode(
                id="ignis_cult",
                name="Ignis Cult",
                source_file=str(place_lore_path),
                node_type="group",
            ),
            "justice": CombinedCharacterNode(
                id="justice",
                name="Justice",
                source_file=str(place_lore_path),
                node_type="character",
            ),
            "stone": CombinedCharacterNode(
                id="stone",
                name="Stone",
                source_file=str(place_lore_path),
                node_type="character",
            ),
            "students": CombinedCharacterNode(
                id="students",
                name="Students",
                source_file=str(place_lore_path),
                node_type="character",
            ),
            "family_tree": CombinedCharacterNode(
                id="family_tree",
                name="Family Tree",
                source_file=str(family_tree_path),
                node_type="source_document",
            ),
            "mrs_nightbloom": CombinedCharacterNode(
                id="mrs_nightbloom",
                name="Mrs Nightbloom",
                source_file="world_building/lore/session_notes/Family_Tree.md",
                node_type="character",
            ),
        },
        edges=[
            CombinedRelationshipEdge(
                source="source_document__atlantia_lore",
                target="atlantia",
                relationship_type="place",
                relationship_label="Place",
                evidence=["Atlantia is home to Jory Ravenmark."],
            ),
            CombinedRelationshipEdge(
                source="source_document__atlantia_lore",
                target="jory_ravenmark",
                relationship_type="home",
                relationship_label="Home",
                evidence=["Atlantia is home to Jory Ravenmark."],
            ),
            CombinedRelationshipEdge(
                source="source_document__atlantia_lore",
                target="orin_nightbloom",
                relationship_type="studied",
                relationship_label="Studied",
                evidence=["Orin Nightbloom studied at Sunstone Mage College."],
            ),
            CombinedRelationshipEdge(
                source="source_document__atlantia_lore",
                target="sunstone_mage_college",
                relationship_type="contains",
                relationship_label="Contains",
                evidence=["Orin Nightbloom studied at Sunstone Mage College."],
            ),
            CombinedRelationshipEdge(
                source="source_document__atlantia_lore",
                target="ignis_cult",
                relationship_type="threat",
                relationship_label="Threat",
            ),
            CombinedRelationshipEdge(
                source="source_document__atlantia_lore",
                target="stone",
                relationship_type="ally",
                relationship_label="Ally",
                evidence=["Stone and Students are common words here."],
            ),
            CombinedRelationshipEdge(
                source="source_document__atlantia_lore",
                target="students",
                relationship_type="referenced",
                relationship_label="Referenced",
                evidence=["Stone and Students are common words here."],
            ),
            CombinedRelationshipEdge(
                source="orin_nightbloom",
                target="sunstone_mage_college",
                relationship_type="studied",
                relationship_label="Studied",
            ),
            CombinedRelationshipEdge(
                source="family_tree",
                target="atlantia",
                relationship_type="mentions",
                relationship_label="Mentions",
                evidence=["Atlantia is listed beside Mrs Nightbloom."],
            ),
            CombinedRelationshipEdge(
                source="family_tree",
                target="mrs_nightbloom",
                relationship_type="mentions",
                relationship_label="Mentions",
                evidence=["Atlantia is listed beside Mrs Nightbloom."],
            ),
        ],
    )

    place_graph = place_lore_graph(graph)
    atlantia_heading_id = "source_heading__sourcedocumentatlantialore__line_1__atlantialore"
    college_heading_id = "source_heading__sourcedocumentatlantialore__line_3__sunstonemagecollege"
    family_heading_id = "source_heading__familytree__line_1__familytree"

    assert set(place_graph.characters) == {
        "source_document__atlantia_lore",
        "family_tree",
        atlantia_heading_id,
        college_heading_id,
        family_heading_id,
        "atlantia",
        "sunstone_mage_college",
        "jory_ravenmark",
        "orin_nightbloom",
        "mrs_nightbloom",
    }
    assert {(edge.source, edge.target) for edge in place_graph.edges} == {
        ("source_document__atlantia_lore", atlantia_heading_id),
        (atlantia_heading_id, "atlantia"),
        (atlantia_heading_id, "jory_ravenmark"),
        (atlantia_heading_id, college_heading_id),
        (college_heading_id, "sunstone_mage_college"),
        (college_heading_id, "orin_nightbloom"),
        ("sunstone_mage_college", "orin_nightbloom"),
        ("family_tree", family_heading_id),
        (family_heading_id, "atlantia"),
        (family_heading_id, "mrs_nightbloom"),
    }
    labels_by_edge = {
        (edge.source, edge.target): edge.relationship_label
        for edge in place_graph.edges
    }
    assert labels_by_edge[("source_document__atlantia_lore", atlantia_heading_id)] == ""
    assert labels_by_edge[(atlantia_heading_id, "atlantia")] == ""
    assert labels_by_edge[(atlantia_heading_id, "jory_ravenmark")] == "Home"
    assert labels_by_edge[(family_heading_id, "mrs_nightbloom")] == "Mentions"
    table_rows = place_lore_connection_rows(place_graph)
    assert {row["Connection Type"] for row in table_rows} == {"Character"}
    assert {row["Connection"] for row in table_rows} == {
        "Jory Ravenmark",
        "Orin Nightbloom",
        "Mrs Nightbloom",
    }
    assert {row["Relationship"] for row in table_rows} == {"Home", "Studied", "Mentions"}
    assert place_graph.characters[atlantia_heading_id].node_type == "source_heading_1"
    assert place_graph.characters[college_heading_id].node_type == "source_heading_2"
    assert all(node.name != "Faculty" for node in place_graph.characters.values())
    assert all(node.name != "Ignored Detail" for node in place_graph.characters.values())
    assert "justice" not in place_graph.characters
    assert "ignis_cult" not in place_graph.characters
    assert "stone" not in place_graph.characters
    assert "students" not in place_graph.characters


def test_place_lore_dot_uses_source_heading_place_character_columns():
    graph = CombinedCharacterGraph(
        characters={
            "source_document__atlantia_lore": CombinedCharacterNode(
                id="source_document__atlantia_lore",
                name="Atlantia Lore",
                source_file="world_building/lore/places/Atlantia_Lore.md",
                node_type="source_document",
            ),
            "atlantia": CombinedCharacterNode(
                id="atlantia",
                name="Atlantia",
                source_file="world_building/lore/places/Atlantia_Lore.md",
                node_type="place",
            ),
            "jory_ravenmark": CombinedCharacterNode(
                id="jory_ravenmark",
                name="Jory Ravenmark",
                source_file="world_building/lore/character_sheets/Jory_Ravenmark.md",
                node_type="character",
            ),
            "source_heading__atlantia__location": CombinedCharacterNode(
                id="source_heading__atlantia__location",
                name="Location",
                source_file="world_building/lore/places/Atlantia_Lore.md",
                node_type="source_heading_2",
            ),
            "source_heading__atlantia__districts": CombinedCharacterNode(
                id="source_heading__atlantia__districts",
                name="Districts",
                source_file="world_building/lore/places/Atlantia_Lore.md",
                node_type="source_heading_1",
            ),
            "source_heading__atlantia__faculty": CombinedCharacterNode(
                id="source_heading__atlantia__faculty",
                name="Faculty",
                source_file="world_building/lore/places/Atlantia_Lore.md",
                node_type="source_heading_3",
            ),
        },
        edges=[
            CombinedRelationshipEdge(
                source="source_document__atlantia_lore",
                target="source_heading__atlantia__districts",
                relationship_type="heading",
                relationship_label="",
            ),
            CombinedRelationshipEdge(
                source="source_heading__atlantia__districts",
                target="source_heading__atlantia__location",
                relationship_type="heading",
                relationship_label="",
            ),
            CombinedRelationshipEdge(
                source="source_heading__atlantia__location",
                target="source_heading__atlantia__faculty",
                relationship_type="heading",
                relationship_label="",
            ),
            CombinedRelationshipEdge(
                source="source_heading__atlantia__location",
                target="atlantia",
                relationship_type="location",
                relationship_label="Location",
            ),
            CombinedRelationshipEdge(
                source="atlantia",
                target="jory_ravenmark",
                relationship_type="home",
                relationship_label="Home",
            ),
        ],
    )

    dot = combined_relationship_dot(
        graph,
        main_character_ids=set(graph.characters),
        graphviz_config={"column_layout": "place_lore"},
    )

    source_column = dot[dot.index('subgraph "cluster_column_0_source_documents_places"') :]
    heading_1_column = dot[dot.index('subgraph "cluster_column_1_markdown_heading_1"') :]
    heading_2_column = dot[dot.index('subgraph "cluster_column_2_markdown_heading_2"') :]
    heading_3_column = dot[dot.index('subgraph "cluster_column_3_markdown_heading_3"') :]

    assert source_column.index('"source_document__atlantia_lore"') < source_column.index('subgraph "cluster_column_1_markdown_heading_1"')
    assert source_column.index('"atlantia"') < source_column.index('subgraph "cluster_column_1_markdown_heading_1"')
    assert heading_1_column.index('"source_heading__atlantia__districts"') < heading_1_column.index('subgraph "cluster_column_2_markdown_heading_2"')
    assert heading_2_column.index('"source_heading__atlantia__location"') < heading_2_column.index('subgraph "cluster_column_3_markdown_heading_3"')
    assert heading_3_column.index('"source_heading__atlantia__faculty"') < heading_3_column.index('subgraph "cluster_column_4_character_connections"')
    assert (
        'subgraph "cluster_column_4_character_connections" '
        '{ rank=same; style=invis; "graph_column_4"; "jory_ravenmark"; }'
    ) in dot
    assert '"atlantia" -> "jory_ravenmark" [label="Home", tailport=e, headport=w];' in dot


def test_session_note_lore_graph_uses_headings_groups_characters_and_places(tmp_path):
    session_dir = tmp_path / "session_notes"
    session_dir.mkdir()
    session_path = session_dir / "Family_Tree.md"
    session_path.write_text(
        "\n".join(
            [
                "# Family Tree",
                "The Ravenmark Family keeps watch over Atlantia.",
                "## Ravenmark Trouble",
                "Jory Ravenmark found trouble in Atlantia.",
                "### Empty Aside",
                "Nothing extracted here.",
            ]
        ),
        encoding="utf-8",
    )
    graph = CombinedCharacterGraph(
        characters={
            "family_tree": CombinedCharacterNode(
                id="family_tree",
                name="Family Tree",
                source_file=str(session_path),
                node_type="source_document",
            ),
            "ravenmark_family": CombinedCharacterNode(
                id="ravenmark_family",
                name="Ravenmark Family",
                source_file=str(session_path),
                node_type="group",
            ),
            "jory_ravenmark": CombinedCharacterNode(
                id="jory_ravenmark",
                name="Jory Ravenmark",
                source_file="world_building/lore/character_sheets/Jory_Ravenmark.md",
                node_type="character",
            ),
            "atlantia": CombinedCharacterNode(
                id="atlantia",
                name="Atlantia",
                source_file="world_building/lore/places/Atlantia_Lore.md",
                node_type="place",
            ),
        },
        edges=[
            CombinedRelationshipEdge(
                source="family_tree",
                target="ravenmark_family",
                relationship_type="mentions",
                relationship_label="Mentions",
                evidence=["The Ravenmark Family keeps watch over Atlantia."],
            ),
            CombinedRelationshipEdge(
                source="family_tree",
                target="jory_ravenmark",
                relationship_type="mentions",
                relationship_label="Mentions",
                evidence=["Jory Ravenmark found trouble in Atlantia."],
            ),
            CombinedRelationshipEdge(
                source="family_tree",
                target="atlantia",
                relationship_type="place",
                relationship_label="Place",
                evidence=["Jory Ravenmark found trouble in Atlantia."],
            ),
        ],
    )

    lore_graph = session_note_lore_graph(graph)
    family_heading_id = "source_heading__familytree__line_1__familytree"
    trouble_heading_id = "source_heading__familytree__line_3__ravenmarktrouble"

    assert set(lore_graph.characters) == {
        "family_tree",
        "ravenmark_family",
        "jory_ravenmark",
        "atlantia",
        family_heading_id,
        trouble_heading_id,
    }
    assert {(edge.source, edge.target) for edge in lore_graph.edges} == {
        ("family_tree", family_heading_id),
        (family_heading_id, "ravenmark_family"),
        (family_heading_id, trouble_heading_id),
        (trouble_heading_id, "jory_ravenmark"),
        (trouble_heading_id, "atlantia"),
    }
    assert all(node.name != "Empty Aside" for node in lore_graph.characters.values())

    dot = combined_relationship_dot(
        lore_graph,
        main_character_ids=set(lore_graph.characters),
        graphviz_config={"column_layout": "session_note_lore"},
    )
    assert 'subgraph "cluster_column_0_source_documents_groups"' in dot
    assert 'subgraph "cluster_column_4_character_connections"' in dot
    assert dot.index('"family_tree"') < dot.index('"ravenmark_family"')
    assert '"jory_ravenmark"' in dot
    assert '"atlantia"' in dot


def test_session_note_graph_keeps_only_session_note_connections():
    graph = CombinedCharacterGraph(
        characters={
            "family_tree": CombinedCharacterNode(
                id="family_tree",
                name="Family Tree",
                source_file="world_building/lore/session_notes/2026-07-19_Family_Tree.md",
                node_type="source_document",
            ),
            "jory_ravenmark": CombinedCharacterNode(
                id="jory_ravenmark",
                name="Jory Ravenmark",
                source_file="world_building/lore/character_sheets/Jory_Ravenmark.md",
                node_type="character",
            ),
            "source_document__atlantia_lore": CombinedCharacterNode(
                id="source_document__atlantia_lore",
                name="Atlantia Lore",
                source_file="world_building/lore/places/Atlantia_Lore.md",
                node_type="source_document",
            ),
        },
        edges=[
            CombinedRelationshipEdge(
                source="family_tree",
                target="jory_ravenmark",
                relationship_type="mentions",
                relationship_label="Mentions",
            ),
            CombinedRelationshipEdge(
                source="source_document__atlantia_lore",
                target="jory_ravenmark",
                relationship_type="home",
                relationship_label="Home",
            ),
        ],
    )

    filtered = session_note_graph(graph)

    assert set(filtered.characters) == {"family_tree", "jory_ravenmark"}
    assert [(edge.source, edge.target) for edge in filtered.edges] == [("family_tree", "jory_ravenmark")]


def test_structured_knowledge_view_hides_source_document_knots():
    graph = CombinedCharacterGraph(
        characters={
            "source_document__atlantia_lore": CombinedCharacterNode(
                id="source_document__atlantia_lore",
                name="Atlantia Lore",
                source_file="world_building/lore/places/Atlantia_Lore.md",
                node_type="source_document",
            ),
            "jory_ravenmark": CombinedCharacterNode(
                id="jory_ravenmark",
                name="Jory Ravenmark",
                source_file="world_building/lore/character_sheets/Jory_Ravenmark.md",
                node_type="character",
            ),
        },
        edges=[
            CombinedRelationshipEdge(
                source="source_document__atlantia_lore",
                target="jory_ravenmark",
                relationship_type="home",
                relationship_label="Home",
            ),
        ],
    )

    filtered = graph_without_lore_source_knots(graph)

    assert filtered.characters == {}
    assert filtered.edges == []
