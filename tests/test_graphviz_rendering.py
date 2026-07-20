from character_graph.combined_graph import (
    CombinedCharacterGraph,
    CombinedCharacterNode,
    CombinedRelationshipEdge,
    combined_relationship_dot,
)
from graphviz_rendering import (
    DIRECTORY_FILE_VIEW_TAB,
    PARTY_VIEW_TAB,
    PLACES_HEADING_VIEW_TAB,
    SESSION_FILE_VIEW_TAB,
    SINGLE_CHARACTER_TAB,
    PLACES_FILE_VIEW_TAB,
    graph_without_lore_source_knots,
    graph_tab_names,
    place_lore_connection_rows,
    place_lore_graph,
    lore_information_rows,
    session_note_graph,
    session_note_lore_graph,
)


def test_graph_tabs_follow_active_main_tab():
    assert graph_tab_names("Characters") == [SINGLE_CHARACTER_TAB, PARTY_VIEW_TAB]
    assert graph_tab_names("Places") == [
        PLACES_FILE_VIEW_TAB,
        PLACES_HEADING_VIEW_TAB,
    ]
    assert graph_tab_names("Session Notes") == [
        SESSION_FILE_VIEW_TAB,
        DIRECTORY_FILE_VIEW_TAB,
    ]


def test_place_lore_graph_keeps_source_place_and_character_connections(tmp_path):
    place_lore_path = tmp_path / "Atlantia_Lore.md"
    place_lore_path.write_text(
        "\n".join(
            [
                "# Atlantia Lore",
                "Atlantia is home to Jory Ravenmark.",
                "## Town Overview",
                "Atlantia grew around the harbor, the watch tower, and the roads inland.",
                "## The Harbor",
                "Jory Ravenmark watched the tide from the Harbor.",
                "## The Watch Tower",
                "Mrs Nightbloom kept watch from the Watch Tower.",
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
                target="jory_ravenmark",
                relationship_type="home",
                relationship_label="Home",
                evidence=["Jory Ravenmark watched the tide from the Harbor."],
            ),
            CombinedRelationshipEdge(
                source="source_document__atlantia_lore",
                target="mrs_nightbloom",
                relationship_type="mentions",
                relationship_label="Mentions",
                evidence=["Mrs Nightbloom kept watch from the Watch Tower."],
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
    harbor_heading_id = "source_heading__sourcedocumentatlantialore__line_5__theharbor"
    watch_tower_heading_id = "source_heading__sourcedocumentatlantialore__line_7__thewatchtower"
    college_heading_id = "source_heading__sourcedocumentatlantialore__line_9__sunstonemagecollege"
    family_heading_id = "source_heading__familytree__line_1__familytree"

    assert set(place_graph.characters) == {
        "source_document__atlantia_lore",
        "family_tree",
        atlantia_heading_id,
        harbor_heading_id,
        watch_tower_heading_id,
        college_heading_id,
        family_heading_id,
        "atlantia",
        "jory_ravenmark",
        "orin_nightbloom",
        "mrs_nightbloom",
    }
    assert {(edge.source, edge.target) for edge in place_graph.edges} == {
        ("source_document__atlantia_lore", atlantia_heading_id),
        (atlantia_heading_id, "atlantia"),
        (atlantia_heading_id, harbor_heading_id),
        (atlantia_heading_id, watch_tower_heading_id),
        (atlantia_heading_id, college_heading_id),
        ("atlantia", harbor_heading_id),
        ("atlantia", watch_tower_heading_id),
        ("atlantia", college_heading_id),
        (atlantia_heading_id, "jory_ravenmark"),
        (harbor_heading_id, "jory_ravenmark"),
        (watch_tower_heading_id, "mrs_nightbloom"),
        (college_heading_id, "orin_nightbloom"),
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
    assert labels_by_edge[("atlantia", harbor_heading_id)] == "Contains"
    assert labels_by_edge[("atlantia", watch_tower_heading_id)] == "Contains"
    assert labels_by_edge[("atlantia", college_heading_id)] == "Contains"
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
    assert place_graph.characters[harbor_heading_id].node_type == "source_heading_place_2"
    assert place_graph.characters[harbor_heading_id].name == "Harbor"
    assert place_graph.characters[watch_tower_heading_id].node_type == "source_heading_place_2"
    assert place_graph.characters[watch_tower_heading_id].name == "Watch Tower"
    assert place_graph.characters[college_heading_id].node_type == "source_heading_place_2"
    note_rows = lore_information_rows(place_graph)
    assert {
        (row["Heading"], row["Summary"])
        for row in note_rows
    } == {
        ("Town Overview", "Atlantia grew around the harbor, the watch tower, and the roads inland."),
        ("Faculty", "Mrs Nightbloom keeps old records here."),
    }
    assert all(node.name != "Faculty" for node in place_graph.characters.values())
    assert all(node.name != "Ignored Detail" for node in place_graph.characters.values())
    assert "justice" not in place_graph.characters
    assert "ignis_cult" not in place_graph.characters
    assert "stone" not in place_graph.characters
    assert "students" not in place_graph.characters

    file_view_graph = place_lore_graph(graph, source_file=str(place_lore_path))
    assert "source_document__atlantia_lore" in file_view_graph.characters
    assert "family_tree" not in file_view_graph.characters
    assert "mrs_nightbloom" in file_view_graph.characters
    directory_file_view_graph = place_lore_graph(
        graph,
        source_file=str(place_lore_path),
        hide_source_document_roots=True,
    )
    assert "source_document__atlantia_lore" not in directory_file_view_graph.characters
    assert "mrs_nightbloom" in directory_file_view_graph.characters

    heading_view_graph = place_lore_graph(graph, heading_id=college_heading_id)
    assert set(heading_view_graph.characters) == {
        "source_document__atlantia_lore",
        atlantia_heading_id,
        "atlantia",
        college_heading_id,
        "orin_nightbloom",
    }


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
                name="Harbor",
                source_file="world_building/lore/places/Atlantia_Lore.md",
                node_type="source_heading_place_2",
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
    assert '"source_heading__atlantia__location" [label="Harbor", fillcolor="#dcfce7", color="#94a3b8", shape="component"' in dot
    assert (
        'subgraph "cluster_column_4_character_connections" '
        '{ rank=same; style=invis; "graph_column_4"; "jory_ravenmark"; }'
    ) in dot
    assert '"atlantia" -> "jory_ravenmark" [label="Home", tailport=e, headport=w];' in dot


def test_directory_place_lore_dot_keeps_source_documents_in_column_zero():
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
            "source_heading__atlantia__harbor": CombinedCharacterNode(
                id="source_heading__atlantia__harbor",
                name="Harbor",
                source_file="world_building/lore/places/Atlantia_Lore.md",
                node_type="source_heading_place_2",
            ),
            "source_heading__atlantia__faculty": CombinedCharacterNode(
                id="source_heading__atlantia__faculty",
                name="Faculty",
                source_file="world_building/lore/places/Atlantia_Lore.md",
                node_type="source_heading_3",
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
                target="atlantia",
                relationship_type="place",
                relationship_label="",
            ),
            CombinedRelationshipEdge(
                source="atlantia",
                target="source_heading__atlantia__harbor",
                relationship_type="contains",
                relationship_label="Contains",
            ),
            CombinedRelationshipEdge(
                source="source_heading__atlantia__harbor",
                target="source_heading__atlantia__faculty",
                relationship_type="heading",
                relationship_label="",
            ),
            CombinedRelationshipEdge(
                source="source_heading__atlantia__harbor",
                target="jory_ravenmark",
                relationship_type="home",
                relationship_label="Home",
            ),
        ],
    )

    dot = combined_relationship_dot(
        graph,
        main_character_ids=set(graph.characters),
        graphviz_config={"column_layout": "place_lore_directory"},
    )

    source_column = dot[dot.index('subgraph "cluster_column_0_source_documents"') :]
    heading_1_column = dot[dot.index('subgraph "cluster_column_1_markdown_heading_1"') :]
    heading_2_column = dot[dot.index('subgraph "cluster_column_2_markdown_heading_2"') :]
    heading_3_column = dot[dot.index('subgraph "cluster_column_3_markdown_heading_3"') :]

    assert source_column.index('"source_document__atlantia_lore"') < source_column.index('subgraph "cluster_column_1_markdown_heading_1"')
    assert heading_1_column.index('"atlantia"') < heading_1_column.index('subgraph "cluster_column_2_markdown_heading_2"')
    assert heading_2_column.index('"source_heading__atlantia__harbor"') < heading_2_column.index('subgraph "cluster_column_3_markdown_heading_3"')
    assert heading_3_column.index('"source_heading__atlantia__faculty"') < heading_3_column.index('subgraph "cluster_column_4_character_connections"')
    assert '"source_heading__atlantia__harbor" [label="Harbor", fillcolor="#dcfce7", color="#94a3b8", shape="component"' in dot


def test_directory_session_lore_dot_keeps_groups_in_column_zero_and_places_in_heading_one():
    graph = CombinedCharacterGraph(
        characters={
            "session_1": CombinedCharacterNode(
                id="session_1",
                name="Session 1",
                source_file="world_building/lore/session_notes/Session_1.md",
                node_type="source_document",
            ),
            "ravenmark_family": CombinedCharacterNode(
                id="ravenmark_family",
                name="Ravenmark Family",
                source_file="world_building/lore/session_notes/Session_1.md",
                node_type="group",
            ),
            "atlantia": CombinedCharacterNode(
                id="atlantia",
                name="Atlantia",
                source_file="world_building/lore/places/Atlantia_Lore.md",
                node_type="place",
            ),
            "source_heading__session_1__harbor": CombinedCharacterNode(
                id="source_heading__session_1__harbor",
                name="Harbor",
                source_file="world_building/lore/session_notes/Session_1.md",
                node_type="source_heading_place_2",
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
                source="session_1",
                target="ravenmark_family",
                relationship_type="mentions",
                relationship_label="",
            ),
            CombinedRelationshipEdge(
                source="session_1",
                target="atlantia",
                relationship_type="place",
                relationship_label="Place",
            ),
            CombinedRelationshipEdge(
                source="atlantia",
                target="source_heading__session_1__harbor",
                relationship_type="contains",
                relationship_label="Contains",
            ),
            CombinedRelationshipEdge(
                source="source_heading__session_1__harbor",
                target="jory_ravenmark",
                relationship_type="mentions",
                relationship_label="Mentions",
            ),
        ],
    )

    dot = combined_relationship_dot(
        graph,
        main_character_ids=set(graph.characters),
        graphviz_config={"column_layout": "session_note_lore_directory"},
    )

    source_column = dot[dot.index('subgraph "cluster_column_0_source_documents_groups"') :]
    heading_1_column = dot[dot.index('subgraph "cluster_column_1_markdown_heading_1"') :]
    heading_2_column = dot[dot.index('subgraph "cluster_column_2_markdown_heading_2"') :]

    assert source_column.index('"session_1"') < source_column.index('subgraph "cluster_column_1_markdown_heading_1"')
    assert source_column.index('"ravenmark_family"') < source_column.index('subgraph "cluster_column_1_markdown_heading_1"')
    assert heading_1_column.index('"atlantia"') < heading_1_column.index('subgraph "cluster_column_2_markdown_heading_2"')
    assert heading_2_column.index('"source_heading__session_1__harbor"') < heading_2_column.index('subgraph "cluster_column_3_markdown_heading_3"')


def test_session_note_lore_graph_uses_headings_groups_characters_and_places(tmp_path):
    session_dir = tmp_path / "session_notes"
    session_dir.mkdir()
    session_path = session_dir / "Family_Tree.md"
    side_session_path = session_dir / "Side_Notes.md"
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
    side_session_path.write_text("# Side Notes\n\nJory Ravenmark visits Atlantia.", encoding="utf-8")
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
            "mary_ravenmark": CombinedCharacterNode(
                id="mary_ravenmark",
                name="Mary Ravenmark",
                source_file="world_building/lore/character_sheets/Mary_Ravenmark.md",
                node_type="character",
            ),
            "atlantia": CombinedCharacterNode(
                id="atlantia",
                name="Atlantia",
                source_file="world_building/lore/places/Atlantia_Lore.md",
                node_type="place",
            ),
            "side_notes": CombinedCharacterNode(
                id="side_notes",
                name="Side Notes",
                source_file=str(side_session_path),
                node_type="source_document",
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
            CombinedRelationshipEdge(
                source="side_notes",
                target="jory_ravenmark",
                relationship_type="mentions",
                relationship_label="Mentions",
                evidence=["Jory Ravenmark visits Atlantia."],
            ),
            CombinedRelationshipEdge(
                source="ravenmark_family",
                target="mary_ravenmark",
                relationship_type="family",
                relationship_label="Family",
                evidence=["Mary Ravenmark is linked to the Ravenmark Family."],
            ),
        ],
    )

    lore_graph = session_note_lore_graph(graph)
    family_heading_id = "source_heading__familytree__line_1__familytree"
    trouble_heading_id = "source_heading__familytree__line_3__ravenmarktrouble"

    assert set(lore_graph.characters) == {
        "family_tree",
        "side_notes",
        "ravenmark_family",
        "jory_ravenmark",
        "atlantia",
        family_heading_id,
        trouble_heading_id,
        "source_heading__sidenotes__line_1__sidenotes",
    }
    assert {(edge.source, edge.target) for edge in lore_graph.edges} == {
        ("family_tree", family_heading_id),
        (family_heading_id, "ravenmark_family"),
        (family_heading_id, trouble_heading_id),
        (trouble_heading_id, "jory_ravenmark"),
        (trouble_heading_id, "atlantia"),
        ("side_notes", "source_heading__sidenotes__line_1__sidenotes"),
        ("source_heading__sidenotes__line_1__sidenotes", "jory_ravenmark"),
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
    assert "mary_ravenmark" not in lore_graph.characters

    file_view_graph = session_note_lore_graph(
        graph,
        source_file=str(session_path),
        fanout_linked_characters=True,
    )
    assert "family_tree" in file_view_graph.characters
    assert "side_notes" not in file_view_graph.characters
    assert "mary_ravenmark" in file_view_graph.characters
    assert ("ravenmark_family", "mary_ravenmark") in {
        (edge.source, edge.target)
        for edge in file_view_graph.edges
    }
    directory_file_view_graph = session_note_lore_graph(
        graph,
        source_file=str(session_path),
        fanout_linked_characters=True,
        hide_source_document_roots=True,
    )
    assert "family_tree" not in directory_file_view_graph.characters
    assert "side_notes" not in directory_file_view_graph.characters
    assert "mary_ravenmark" in directory_file_view_graph.characters
    assert all(
        edge.source != "family_tree" and edge.target != "family_tree"
        for edge in directory_file_view_graph.edges
    )

    heading_view_graph = session_note_lore_graph(graph, heading_id=trouble_heading_id)
    assert set(heading_view_graph.characters) == {
        "family_tree",
        family_heading_id,
        trouble_heading_id,
        "jory_ravenmark",
        "atlantia",
    }
    assert "ravenmark_family" not in heading_view_graph.characters


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
