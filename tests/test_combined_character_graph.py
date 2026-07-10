from character_graph.combined_graph import (
    build_combined_character_graph,
    combined_relationship_dot,
    combined_relationship_rows,
)
from character_graph.storage import load_graph


def test_combined_graph_links_neal_to_referenced_existing_characters():
    graphs = [
        load_graph("data/character_graph/Neal Lovington.graph.json"),
        load_graph("data/character_graph/Jory_Ravenmark.graph.json"),
        load_graph("data/character_graph/Orin Nightbloom.graph.json"),
    ]

    combined = build_combined_character_graph([graph for graph in graphs if graph is not None])

    assert ("neal_lovington", "jory_ravenmark", "client") in {
        (edge.source, edge.target, edge.relationship_type) for edge in combined.edges
    }
    assert ("neal_lovington", "orin_nightbloom", "client") in {
        (edge.source, edge.target, edge.relationship_type) for edge in combined.edges
    }
    jory_edge = next(
        edge
        for edge in combined.edges
        if edge.source == "neal_lovington" and edge.target == "jory_ravenmark" and edge.relationship_type == "client"
    )
    orin_edge = next(
        edge
        for edge in combined.edges
        if edge.source == "neal_lovington" and edge.target == "orin_nightbloom" and edge.relationship_type == "client"
    )
    assert "Jory Ravenmark is their favorite client" in " ".join(jory_edge.evidence)
    assert "Orin Nightbloom" in " ".join(orin_edge.evidence)


def test_combined_graph_rows_and_dot_include_cross_character_connections():
    graphs = [
        load_graph("data/character_graph/Neal Lovington.graph.json"),
        load_graph("data/character_graph/Jory_Ravenmark.graph.json"),
        load_graph("data/character_graph/Orin Nightbloom.graph.json"),
    ]
    combined = build_combined_character_graph([graph for graph in graphs if graph is not None])

    rows = combined_relationship_rows(combined)
    dot = combined_relationship_dot(combined)

    assert any(row["Character"] == "Neal Lovington" and row["Connection"] == "Jory Ravenmark" for row in rows)
    assert any(row["Character"] == "Neal Lovington" and row["Connection"] == "Orin Nightbloom" for row in rows)
    assert '"neal_lovington" -> "jory_ravenmark"' in dot
    assert '"neal_lovington" -> "orin_nightbloom"' in dot
