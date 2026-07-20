from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Callable

import streamlit as st

from character_graph.combined_graph import (
    CombinedCharacterGraph,
    CombinedCharacterNode,
    CombinedRelationshipEdge,
    combined_relationship_dot,
    combined_relationship_rows,
    compact,
    full_character_connection_graph,
    is_lore_source_node,
    other_connection_rows,
    other_connections_graph,
)
from character_graph.graphviz_config import load_graphviz_config


@dataclass(frozen=True)
class KnowledgeGraphView:
    key: str
    label: str


@dataclass(frozen=True)
class MarkdownSubheading:
    id: str
    text: str
    level: int
    line_index: int
    parent_id: str


SINGLE_CHARACTER_TAB = "Single Character"
PARTY_VIEW_TAB = "Party View"
PLACES_GRAPH_TAB = "Place Lore"
PLACE_LORE_TAB = PLACES_GRAPH_TAB
FULL_KNOWLEDGE_GRAPH_TAB = "Full Knowledge Graph"

STRUCTURED_CHARACTER_VIEW = KnowledgeGraphView(
    key="character_view",
    label="Single Character",
)
CHARACTER_DATA_ONLY_VIEW = KnowledgeGraphView(
    key="party_view_fixture",
    label="Character Data Only",
)
PLACE_LORE_VIEW = KnowledgeGraphView(
    key="full_structured_graph",
    label="Place Lore",
)
SESSION_MONTH_VIEW = KnowledgeGraphView(
    key="full_structured_graph",
    label="Month Selection",
)
STRUCTURED_KNOWLEDGE_VIEW = KnowledgeGraphView(
    key="full_structured_graph",
    label="Structured Knowledge View",
)
FULL_KNOWLEDGE_VIEW = KnowledgeGraphView(
    key="full_structured_graph",
    label="Full Knowledge Graph",
)
DISALLOWED_PLACE_GRAPH_CHARACTER_KEYS = {"family", "stone", "students"}
PLACE_GRAPH_MARKDOWN_HEADING_RE = re.compile(r"^(?P<marker>#{1,3})\s+(?P<text>.*?)\s*#*\s*$")


def render_knowledge_graph_tabs(
    *,
    combined: CombinedCharacterGraph,
    character_sheet_combined: CombinedCharacterGraph,
    character_sheet_detail_rows: list[dict[str, str]],
    character_nodes: list[CombinedCharacterNode],
    main_character_ids: set[str],
    main_place_ids: set[str],
    graph_revision: int,
    label_font_color: str,
    active_main_tab: str = "Characters",
) -> None:
    tab_names = graph_tab_names(active_main_tab)
    tabs = st.tabs(tab_names)
    for tab, tab_name in zip(tabs, tab_names):
        with tab:
            if tab_name == SINGLE_CHARACTER_TAB:
                render_single_character_tab(
                    combined=combined,
                    character_nodes=character_nodes,
                    main_character_ids=main_character_ids,
                    main_place_ids=main_place_ids,
                    graph_revision=graph_revision,
                    label_font_color=label_font_color,
                )
            elif tab_name == PARTY_VIEW_TAB:
                render_party_view_tab(
                    character_sheet_combined,
                    character_sheet_detail_rows,
                    main_character_ids,
                    label_font_color,
                )
            elif tab_name == PLACES_GRAPH_TAB:
                if active_main_tab == "Session Notes":
                    render_session_note_place_lore_tab(
                        combined=combined,
                        label_font_color=label_font_color,
                    )
                else:
                    render_place_graph_tab(
                        combined=combined,
                        label_font_color=label_font_color,
                    )
            elif tab_name == FULL_KNOWLEDGE_GRAPH_TAB:
                render_full_knowledge_graph_tab(
                    combined=combined,
                    main_character_ids=main_character_ids,
                    main_place_ids=main_place_ids,
                    label_font_color=label_font_color,
                )


def graph_tab_names(active_main_tab: str) -> list[str]:
    if active_main_tab == "Places":
        return [PLACES_GRAPH_TAB, PARTY_VIEW_TAB]
    if active_main_tab == "Session Notes":
        return [PLACE_LORE_TAB, PARTY_VIEW_TAB]
    return [SINGLE_CHARACTER_TAB, PARTY_VIEW_TAB]


def render_single_character_tab(
    *,
    combined: CombinedCharacterGraph,
    character_nodes: list[CombinedCharacterNode],
    main_character_ids: set[str],
    main_place_ids: set[str],
    graph_revision: int,
    label_font_color: str,
) -> None:
    if not character_nodes:
        st.info("Add Main Character Or Place Lore To See Graph Roots.")
        return
    render_structured_character_view(
        combined,
        character_nodes,
        graph_revision,
        main_character_ids,
        main_place_ids,
        label_font_color,
        load_graphviz_config(STRUCTURED_CHARACTER_VIEW.key),
    )


def render_party_view_tab(
    character_sheet_combined: CombinedCharacterGraph,
    character_sheet_detail_rows: list[dict[str, str]],
    main_character_ids: set[str],
    label_font_color: str,
) -> None:
    render_character_data_only_graph_view(
        character_sheet_combined,
        character_sheet_detail_rows,
        main_character_ids,
        label_font_color,
        load_graphviz_config(CHARACTER_DATA_ONLY_VIEW.key),
    )


def render_place_graph_tab(
    *,
    combined: CombinedCharacterGraph,
    label_font_color: str,
) -> None:
    st.subheader(PLACE_LORE_VIEW.label)
    place_graph = place_lore_graph(combined)
    if not place_graph.characters:
        st.info("Add Place Lore To See The Place Lore Graph.")
        return
    graphviz_config = {
        **load_graphviz_config(PLACE_LORE_VIEW.key),
        "column_layout": "place_lore",
    }
    render_relationship_graph(
        place_graph,
        main_character_ids=set(place_graph.characters),
        label_font_color=label_font_color,
        graphviz_config=graphviz_config,
        relationship_rows=place_lore_connection_rows(place_graph),
    )


def render_session_note_place_lore_tab(
    *,
    combined: CombinedCharacterGraph,
    label_font_color: str,
) -> None:
    st.subheader(PLACE_LORE_VIEW.label)
    session_graph = session_note_lore_graph(combined)
    if not session_graph.characters:
        st.info("Add Session Notes To See The Session Notes Graph.")
        return
    graphviz_config = {
        **load_graphviz_config(PLACE_LORE_VIEW.key),
        "column_layout": "session_note_lore",
    }
    render_relationship_graph(
        session_graph,
        main_character_ids=set(session_graph.characters),
        label_font_color=label_font_color,
        graphviz_config=graphviz_config,
        relationship_rows=place_lore_connection_rows(session_graph),
    )


def render_session_note_graph_tab(
    *,
    combined: CombinedCharacterGraph,
    main_character_ids: set[str],
    graph_revision: int,
    label_font_color: str,
) -> None:
    st.subheader(SESSION_MONTH_VIEW.label)
    session_graph = session_note_graph(combined)
    if not session_graph.characters:
        st.info("Add Session Notes To See The Session Note Graph.")
        return
    month_options = session_note_month_options(session_graph)
    selected_month = st.selectbox(
        "Month",
        month_options,
        key=f"session_note_graph_month_{graph_revision}",
    )
    month_graph = filter_session_note_graph_by_month(session_graph, selected_month)
    graphviz_config = load_graphviz_config(SESSION_MONTH_VIEW.key)
    session_source_ids = {
        node_id
        for node_id, node in month_graph.characters.items()
        if is_session_note_node(node)
    }
    render_relationship_graph(
        month_graph,
        main_character_ids=main_character_ids | session_source_ids,
        label_font_color=label_font_color,
        graphviz_config=graphviz_config,
    )


def render_full_knowledge_graph_tab(
    *,
    combined: CombinedCharacterGraph,
    main_character_ids: set[str],
    main_place_ids: set[str],
    label_font_color: str,
) -> None:
    render_relationship_graph(
        combined,
        main_character_ids=main_character_ids,
        main_place_ids=main_place_ids,
        label_font_color=label_font_color,
        graphviz_config=load_graphviz_config(FULL_KNOWLEDGE_VIEW.key),
    )


def render_structured_character_view(
    combined: CombinedCharacterGraph,
    character_nodes: list[CombinedCharacterNode],
    graph_revision: int,
    main_character_ids: set[str],
    main_place_ids: set[str],
    label_font_color: str,
    graphviz_config: dict[str, Any],
) -> None:
    character_tabs = st.tabs([node.name for node in character_nodes])
    for tab, node in zip(character_tabs, character_nodes):
        with tab:
            character_id = node.id
            node_options = combined_graph_root_node_options(character_nodes)
            node_labels = list(node_options)
            default_node_index = node_labels.index(node.name) if node.name in node_options else 0
            selected_node_label = st.selectbox(
                f"Graph Node For {node.name}",
                node_labels,
                index=default_node_index,
                key=f"combined_graph_node_{character_id}_{graph_revision}",
            )
            selected_node_id = node_options[selected_node_label]
            focused_graph = other_connections_graph(combined, selected_node_id)
            associated_rows = other_connection_rows(combined, selected_node_id)
            st.graphviz_chart(
                combined_relationship_dot(
                    focused_graph,
                    selected_node_id,
                    main_character_ids=main_character_ids,
                    main_place_ids=main_place_ids,
                    label_font_color=label_font_color,
                    graphviz_config=graphviz_config,
                ),
                width="stretch",
            )
            if associated_rows:
                st.subheader("Connections")
                st.table(associated_rows, hide_index=True, width="stretch")
            else:
                st.info("No Other Connections Were Found For This Node Yet.")


def render_character_data_only_graph_view(
    combined: CombinedCharacterGraph,
    detail_rows: list[dict[str, str]],
    main_character_ids: set[str],
    label_font_color: str,
    graphviz_config: dict[str, Any],
) -> None:
    st.graphviz_chart(
        combined_relationship_dot(
            full_character_connection_graph(combined),
            main_character_ids=main_character_ids,
            label_font_color=label_font_color,
            graphviz_config=graphviz_config,
        ),
        width="stretch",
    )
    st.subheader("Connections")
    st.table(detail_rows, hide_index=True, width="stretch")


def render_structured_knowledge_view(
    combined: CombinedCharacterGraph,
    main_character_ids: set[str],
    main_place_ids: set[str],
    label_font_color: str,
    graphviz_config: dict[str, Any],
) -> None:
    render_relationship_graph(
        graph_without_lore_source_knots(combined),
        main_character_ids=main_character_ids,
        main_place_ids=main_place_ids,
        label_font_color=label_font_color,
        graphviz_config=graphviz_config,
    )


def render_relationship_graph(
    graph: CombinedCharacterGraph,
    *,
    main_character_ids: set[str] | None = None,
    main_place_ids: set[str] | None = None,
    label_font_color: str,
    graphviz_config: dict[str, Any],
    relationship_rows: list[dict[str, str]] | None = None,
) -> None:
    st.graphviz_chart(
        combined_relationship_dot(
            graph,
            main_character_ids=main_character_ids,
            main_place_ids=main_place_ids,
            label_font_color=label_font_color,
            graphviz_config=graphviz_config,
        ),
        width="stretch",
    )
    st.subheader("Connections")
    st.table(
        relationship_rows if relationship_rows is not None else combined_relationship_rows(graph),
        hide_index=True,
        width="stretch",
    )


def place_lore_graph(
    graph: CombinedCharacterGraph,
) -> CombinedCharacterGraph:
    place_ids = {
        node_id
        for node_id, node in graph.characters.items()
        if node.node_type == "place"
    }
    if not place_ids:
        return CombinedCharacterGraph()

    place_document_ids = {
        source_id
        for edge in graph.edges
        for source_id in edge_source_ids_for_place(edge, graph, place_ids)
    }
    source_document_ids = {
        node_id
        for node_id, node in graph.characters.items()
        if node_id in place_document_ids and node.node_type == "source_document"
    }
    source_to_place_ids = place_ids_by_source_document(graph, source_document_ids, place_ids)
    connected_ids = set(source_document_ids)
    source_headings = markdown_subheadings_by_source(graph, source_document_ids)
    projected_nodes: dict[str, CombinedCharacterNode] = {}
    projected_edges: list[CombinedRelationshipEdge] = []
    for source_id, headings in source_headings.items():
        source = graph.characters[source_id]
        for heading in headings:
            projected_nodes[heading.id] = CombinedCharacterNode(
                id=heading.id,
                name=heading.text,
                source_file=source.source_file,
                node_type=f"source_heading_{heading.level}",
            )
            connected_ids.add(heading.id)
            append_projected_edge(
                projected_edges,
                CombinedRelationshipEdge(
                    source=heading.parent_id or source_id,
                    target=heading.id,
                    relationship_type="heading",
                    relationship_label="",
                ),
            )
    for edge in graph.edges:
        if not edge_connects(edge, place_document_ids, place_ids):
            continue
        source_id = edge.source if edge.source in place_document_ids else edge.target
        place_id = edge.target if edge.source in place_document_ids else edge.source
        source = graph.characters.get(source_id)
        if source is not None and source.node_type == "source_document":
            place = graph.characters.get(place_id)
            heading = markdown_subheading_for_edge(source, source_headings.get(source_id, []), edge, place)
            edge_source = heading.id if heading is not None else source_id
            append_projected_edge(
                projected_edges,
                CombinedRelationshipEdge(
                    source=edge_source,
                    target=place_id,
                    relationship_type=edge.relationship_type,
                    relationship_label="" if heading is not None else edge.relationship_label,
                    evidence=list(edge.evidence),
                    bidirectional=edge.bidirectional,
                ),
            )
        else:
            append_projected_edge(projected_edges, place_character_edge_from_place(edge, graph, place_ids))
    for edge in graph.edges:
        if edge.source in place_ids or edge.target in place_ids:
            connected_ids.update({edge.source, edge.target})
    for edge in graph.edges:
        if edge.source not in source_document_ids and edge.target not in source_document_ids:
            continue
        source_id = edge.source if edge.source in source_document_ids else edge.target
        adjacent_id = edge.target if edge.source in source_document_ids else edge.source
        adjacent = graph.characters.get(adjacent_id)
        if adjacent is None or adjacent.node_type != "character":
            continue
        if is_disallowed_place_graph_character(adjacent):
            continue
        if not source_to_place_ids.get(source_id, set()):
            continue
        heading = markdown_subheading_for_edge(
            graph.characters[source_id],
            source_headings.get(source_id, []),
            edge,
            adjacent,
        )
        if heading is None:
            character_source_ids = source_to_place_ids[source_id]
        else:
            character_source_ids = {heading.id}
        connected_ids.add(adjacent_id)
        for character_source_id in character_source_ids:
            append_projected_edge(
                projected_edges,
                CombinedRelationshipEdge(
                    source=character_source_id,
                    target=adjacent_id,
                    relationship_type=edge.relationship_type,
                    relationship_label=edge.relationship_label,
                    evidence=list(edge.evidence),
                    bidirectional=edge.bidirectional,
                ),
            )
    projected_edges = prune_unassociated_markdown_headings(
        connected_ids,
        projected_nodes,
        projected_edges,
        graph.characters,
    )
    return CombinedCharacterGraph(
        characters={
            **{
                node_id: node
                for node_id, node in graph.characters.items()
                if node_id in connected_ids and node.node_type in {"source_document", "place", "character"}
            },
            **projected_nodes,
        },
        edges=[
            edge
            for edge in projected_edges
            if edge.source in connected_ids and edge.target in connected_ids
        ],
    )


def session_note_lore_graph(graph: CombinedCharacterGraph) -> CombinedCharacterGraph:
    source_document_ids = {
        node_id
        for node_id, node in graph.characters.items()
        if node.node_type == "source_document" and is_session_note_node(node)
    }
    if not source_document_ids:
        return CombinedCharacterGraph()
    connected_ids = set(source_document_ids)
    source_headings = markdown_subheadings_by_source(graph, source_document_ids)
    projected_nodes: dict[str, CombinedCharacterNode] = {}
    projected_edges: list[CombinedRelationshipEdge] = []
    for source_id, headings in source_headings.items():
        source = graph.characters[source_id]
        for heading in headings:
            projected_nodes[heading.id] = CombinedCharacterNode(
                id=heading.id,
                name=heading.text,
                source_file=source.source_file,
                node_type=f"source_heading_{heading.level}",
            )
            connected_ids.add(heading.id)
            append_projected_edge(
                projected_edges,
                CombinedRelationshipEdge(
                    source=heading.parent_id or source_id,
                    target=heading.id,
                    relationship_type="heading",
                    relationship_label="",
                ),
            )
    for edge in graph.edges:
        if edge.source not in source_document_ids and edge.target not in source_document_ids:
            continue
        source_id = edge.source if edge.source in source_document_ids else edge.target
        adjacent_id = edge.target if edge.source in source_document_ids else edge.source
        adjacent = graph.characters.get(adjacent_id)
        if adjacent is None or adjacent.node_type not in {"character", "place", "group"}:
            continue
        heading = markdown_subheading_for_edge(
            graph.characters[source_id],
            source_headings.get(source_id, []),
            edge,
            adjacent,
        )
        connected_ids.add(adjacent_id)
        append_projected_edge(
            projected_edges,
            CombinedRelationshipEdge(
                source=heading.id if heading is not None else source_id,
                target=adjacent_id,
                relationship_type=edge.relationship_type,
                relationship_label=edge.relationship_label if adjacent.node_type in {"character", "place"} else "",
                evidence=list(edge.evidence),
                bidirectional=edge.bidirectional,
            ),
        )
    projected_edges = prune_unassociated_markdown_headings(
        connected_ids,
        projected_nodes,
        projected_edges,
        graph.characters,
    )
    return CombinedCharacterGraph(
        characters={
            **{
                node_id: node
                for node_id, node in graph.characters.items()
                if node_id in connected_ids and node.node_type in {"source_document", "group", "place", "character"}
            },
            **projected_nodes,
        },
        edges=[
            edge
            for edge in projected_edges
            if edge.source in connected_ids and edge.target in connected_ids
        ],
    )


def markdown_subheadings_by_source(
    graph: CombinedCharacterGraph,
    source_ids: set[str],
) -> dict[str, list[MarkdownSubheading]]:
    return {
        source_id: markdown_subheadings_for_source(graph.characters[source_id])
        for source_id in sorted(source_ids)
        if source_id in graph.characters
    }


def markdown_subheadings_for_source(source: CombinedCharacterNode) -> list[MarkdownSubheading]:
    source_path = Path(source.source_file)
    if not source_path.exists():
        return []
    try:
        lines = source_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    headings: list[MarkdownSubheading] = []
    for line_index, line in enumerate(lines):
        match = PLACE_GRAPH_MARKDOWN_HEADING_RE.match(line.strip())
        if match is None:
            continue
        text = match.group("text").strip()
        if not text:
            continue
        level = len(match.group("marker"))
        heading_id = source_heading_node_id(source.id, line_index, text)
        headings.append(
            MarkdownSubheading(
                id=heading_id,
                text=text,
                level=level,
                line_index=line_index,
                parent_id=markdown_heading_parent_id(source.id, headings, level),
            )
        )
    return headings


def markdown_heading_parent_id(
    source_id: str,
    previous_headings: list[MarkdownSubheading],
    level: int,
) -> str:
    for heading in reversed(previous_headings):
        if heading.level < level:
            return heading.id
    return source_id


def markdown_subheading_for_edge(
    source: CombinedCharacterNode,
    headings: list[MarkdownSubheading],
    edge: CombinedRelationshipEdge,
    target: CombinedCharacterNode | None,
) -> MarkdownSubheading | None:
    if not headings:
        return None
    line_index = source_line_index_for_edge(source, edge, target)
    if line_index is not None:
        preceding = [heading for heading in headings if heading.line_index <= line_index]
        if preceding:
            return preceding[-1]
    if target is not None:
        target_key = compact(target.name)
        for heading in headings:
            if compact(heading.text) == target_key:
                return heading
    return headings[0]


def source_line_index_for_edge(
    source: CombinedCharacterNode,
    edge: CombinedRelationshipEdge,
    target: CombinedCharacterNode | None,
) -> int | None:
    source_path = Path(source.source_file)
    if not source_path.exists():
        return None
    try:
        lines = source_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    snippets = [item.strip() for item in edge.evidence if item.strip()]
    if target is not None:
        snippets.append(target.name)
    for snippet in snippets:
        line_index = line_index_for_snippet(lines, snippet)
        if line_index is not None:
            return line_index
    return None


def line_index_for_snippet(lines: list[str], snippet: str) -> int | None:
    normalized_snippet = " ".join(snippet.split())
    for index, line in enumerate(lines):
        if snippet in line or normalized_snippet in " ".join(line.split()):
            return index
    source_text = "\n".join(lines)
    position = source_text.find(snippet)
    if position < 0:
        return None
    return source_text[:position].count("\n")


def source_heading_node_id(source_id: str, line_index: int, text: str) -> str:
    return f"source_heading__{compact(source_id)}__line_{line_index + 1}__{compact(text or 'heading')}"


def place_lore_connection_rows(graph: CombinedCharacterGraph) -> list[dict[str, str]]:
    character_connection_graph = CombinedCharacterGraph(
        characters=graph.characters,
        edges=[
            edge
            for edge in graph.edges
            if edge_has_character_connection(edge, graph)
        ],
    )
    return combined_relationship_rows(character_connection_graph)


def edge_has_character_connection(edge: CombinedRelationshipEdge, graph: CombinedCharacterGraph) -> bool:
    source = graph.characters.get(edge.source)
    target = graph.characters.get(edge.target)
    return source is not None and target is not None and (
        source.node_type == "character" or target.node_type == "character"
    )


def is_markdown_heading_node(node: CombinedCharacterNode | None) -> bool:
    return node is not None and node.node_type.startswith("source_heading")


def prune_unassociated_markdown_headings(
    connected_ids: set[str],
    projected_nodes: dict[str, CombinedCharacterNode],
    projected_edges: list[CombinedRelationshipEdge],
    original_nodes: dict[str, CombinedCharacterNode],
) -> list[CombinedRelationshipEdge]:
    heading_ids = {
        node_id
        for node_id, node in projected_nodes.items()
        if is_markdown_heading_node(node)
    }
    if not heading_ids:
        return projected_edges
    parent_by_heading: dict[str, str] = {}
    associated_heading_ids: set[str] = set()
    all_nodes = {**original_nodes, **projected_nodes}
    for edge in projected_edges:
        if edge.relationship_type == "heading" and edge.target in heading_ids:
            parent_by_heading[edge.target] = edge.source
        source_is_heading = edge.source in heading_ids
        target_is_heading = edge.target in heading_ids
        if source_is_heading == target_is_heading:
            continue
        adjacent_id = edge.target if source_is_heading else edge.source
        adjacent = all_nodes.get(adjacent_id)
        if adjacent is None or adjacent.node_type == "source_document":
            continue
        associated_heading_ids.add(edge.source if source_is_heading else edge.target)
    kept_heading_ids = set(associated_heading_ids)
    pending = list(associated_heading_ids)
    while pending:
        heading_id = pending.pop()
        parent_id = parent_by_heading.get(heading_id)
        if parent_id in heading_ids and parent_id not in kept_heading_ids:
            kept_heading_ids.add(parent_id)
            pending.append(parent_id)
    removed_heading_ids = heading_ids - kept_heading_ids
    for heading_id in removed_heading_ids:
        connected_ids.discard(heading_id)
        projected_nodes.pop(heading_id, None)
    return [
        edge
        for edge in projected_edges
        if edge.source not in removed_heading_ids and edge.target not in removed_heading_ids
    ]


def append_projected_edge(edges: list[CombinedRelationshipEdge], edge: CombinedRelationshipEdge) -> None:
    key = (
        edge.source,
        edge.target,
        edge.relationship_type,
        edge.relationship_label,
    )
    for existing in edges:
        existing_key = (
            existing.source,
            existing.target,
            existing.relationship_type,
            existing.relationship_label,
        )
        if existing_key != key:
            continue
        for evidence in edge.evidence:
            if evidence and evidence not in existing.evidence:
                existing.evidence.append(evidence)
        return
    edges.append(edge)


def is_disallowed_place_graph_character(node: CombinedCharacterNode) -> bool:
    return compact(node.id) in DISALLOWED_PLACE_GRAPH_CHARACTER_KEYS or compact(node.name) in DISALLOWED_PLACE_GRAPH_CHARACTER_KEYS


def edge_source_ids_for_place(
    edge: CombinedRelationshipEdge,
    graph: CombinedCharacterGraph,
    place_ids: set[str],
) -> set[str]:
    if edge.source in place_ids and edge.target in graph.characters:
        return {edge.target}
    if edge.target in place_ids and edge.source in graph.characters:
        return {edge.source}
    return set()


def place_character_edge_from_place(
    edge: CombinedRelationshipEdge,
    graph: CombinedCharacterGraph,
    place_ids: set[str],
) -> CombinedRelationshipEdge:
    if edge.source in place_ids:
        place_id = edge.source
        character_id = edge.target
    elif edge.target in place_ids:
        place_id = edge.target
        character_id = edge.source
    else:
        return edge
    character = graph.characters.get(character_id)
    if character is None or character.node_type != "character":
        return edge
    return CombinedRelationshipEdge(
        source=place_id,
        target=character_id,
        relationship_type=edge.relationship_type,
        relationship_label=edge.relationship_label,
        evidence=list(edge.evidence),
        bidirectional=edge.bidirectional,
    )


def place_ids_by_source_document(
    graph: CombinedCharacterGraph,
    source_ids: set[str],
    place_ids: set[str],
) -> dict[str, set[str]]:
    source_to_place_ids: dict[str, set[str]] = {source_id: set() for source_id in source_ids}
    source_files = {
        source_id: graph.characters[source_id].source_file.replace("\\", "/")
        for source_id in source_ids
        if source_id in graph.characters
    }
    for source_id, source_file in source_files.items():
        for place_id in place_ids:
            place = graph.characters.get(place_id)
            if place is not None and place.source_file.replace("\\", "/") == source_file:
                source_to_place_ids[source_id].add(place_id)
    for edge in graph.edges:
        for source_id in source_ids:
            for place_id in place_ids:
                if edge_connects(edge, {source_id}, {place_id}):
                    source_to_place_ids[source_id].add(place_id)
    return source_to_place_ids


def session_note_graph(graph: CombinedCharacterGraph) -> CombinedCharacterGraph:
    return graph_for_sources(graph, is_session_note_node)


def graph_for_sources(
    graph: CombinedCharacterGraph,
    source_predicate: Callable[[CombinedCharacterNode], bool],
) -> CombinedCharacterGraph:
    source_ids = {
        node_id
        for node_id, node in graph.characters.items()
        if source_predicate(node)
    }
    if not source_ids:
        return CombinedCharacterGraph()
    visible_ids = set(source_ids)
    visible_edges = []
    for edge in graph.edges:
        if edge.source in source_ids or edge.target in source_ids:
            visible_edges.append(edge)
            visible_ids.update({edge.source, edge.target})
    return CombinedCharacterGraph(
        characters={
            node_id: node
            for node_id, node in graph.characters.items()
            if node_id in visible_ids and node.node_type in {"character", "place", "source_document"}
        },
        edges=[
            edge
            for edge in visible_edges
            if edge.source in visible_ids and edge.target in visible_ids
        ],
    )


def graph_without_lore_source_knots(graph: CombinedCharacterGraph) -> CombinedCharacterGraph:
    visible_characters = {
        node_id: node
        for node_id, node in graph.characters.items()
        if not is_hidden_full_knowledge_source_node(node)
    }
    visible_edges = [
        edge
        for edge in graph.edges
        if edge.source in visible_characters and edge.target in visible_characters
    ]
    connected_ids = {edge.source for edge in visible_edges} | {edge.target for edge in visible_edges}
    return CombinedCharacterGraph(
        characters={
            node_id: node
            for node_id, node in visible_characters.items()
            if node_id in connected_ids
        },
        edges=visible_edges,
    )


def combined_graph_root_node_options(nodes: list[CombinedCharacterNode]) -> dict[str, str]:
    return {node.name: node.id for node in nodes}


def session_note_month_options(graph: CombinedCharacterGraph) -> list[str]:
    months = {
        session_note_month(node)
        for node in graph.characters.values()
        if is_session_note_node(node)
    }
    return ["All Months", *sorted(months)]


def filter_session_note_graph_by_month(graph: CombinedCharacterGraph, month: str) -> CombinedCharacterGraph:
    if month == "All Months":
        return graph
    source_ids = {
        node_id
        for node_id, node in graph.characters.items()
        if is_session_note_node(node) and session_note_month(node) == month
    }
    if not source_ids:
        return CombinedCharacterGraph()
    visible_ids = set(source_ids)
    visible_edges = []
    for edge in graph.edges:
        if edge.source in source_ids or edge.target in source_ids:
            visible_edges.append(edge)
            visible_ids.update({edge.source, edge.target})
    return CombinedCharacterGraph(
        characters={node_id: node for node_id, node in graph.characters.items() if node_id in visible_ids},
        edges=visible_edges,
    )


def session_note_month(node: CombinedCharacterNode) -> str:
    source_text = f"{node.source_file} {node.name}"
    match = re.search(r"(?P<year>20\d{2})[-_](?P<month>0[1-9]|1[0-2])", source_text)
    if match:
        return f"{match.group('year')}-{match.group('month')}"
    return "Undated"


def is_hidden_full_knowledge_source_node(node: CombinedCharacterNode | None) -> bool:
    if is_lore_source_node(node):
        return True
    if node is None or node.node_type != "place":
        return False
    source_file = node.source_file.replace("\\", "/")
    if not is_place_lore_path(Path(source_file)):
        return False
    return compact(node.name) == compact(Path(source_file).stem)


def is_place_lore_node(node: CombinedCharacterNode) -> bool:
    source_file = node.source_file.replace("\\", "/")
    return is_place_lore_path(Path(source_file)) or (
        node.node_type == "source_document" and "/places/" in source_file.lower()
    )


def is_place_source_document_node(node: CombinedCharacterNode) -> bool:
    source_file = node.source_file.replace("\\", "/")
    return node.node_type == "source_document" and is_place_lore_path(Path(source_file))


def edge_connects(edge, left_ids: set[str], right_ids: set[str]) -> bool:
    return (edge.source in left_ids and edge.target in right_ids) or (
        edge.target in left_ids and edge.source in right_ids
    )


def is_session_note_node(node: CombinedCharacterNode) -> bool:
    source_file = node.source_file.replace("\\", "/").lower()
    return (
        "/session_notes/" in source_file
        or source_file.endswith("/session_notes.md")
        or compact(Path(source_file).stem) in {"sessionnote", "sessionnotes"}
    )


def is_place_lore_path(path: Path) -> bool:
    return "places" in path.parts
