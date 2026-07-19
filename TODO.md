# UI Bug Reports
- pull the latest changes from the main before writing code.
- Update `ui_issue_report.md` after UI bugs are fixed. 
- Remove graph-edge report grade from the UI.
- 
 

## Knowledge Graph Display Columns

Column 0: Family Names
Column 1: Main Characters
Column 2: Secondary Characters & places

Order all items in the graph based on how many times they are mentioned in the lore.
Allow viewing the graph in two modes, one mode that shows the whole graph and one which shows the connections associated with a single character.

Update the connection type shown on the graph so it shows the most prominent connection between characters or places. 

In the tabular view below, the graph shows each connection a separate table cell for each evidence field rather than combining them with a - characters. 

## Session Planing
1) Get new screenshot of the existing behavior with the following test data `world_building/import/Session_Notes.txt`
2) Compare the fidelity of the extracted knowledge graph to the existing file in `docs/screenshots/Knowledge_Graph.png`
3) Write out a report under `reports/knowledge_graph_report.md` indicating what the current UI does well and how it can be improved.
4) When UI bugs related to the knowledge graph functionality are fixed `update ui_issue_report.md` 
5) Write a 3rd design doc KNOWLEDGE_GRAPH_DESIGN3.md discussing the best way of addressing the issue described in update ui_issue_report.md

Commit to `feature/knowledge_graph` prior to implementing changes

## Hidden Knowledge Graph 

- Replaced the Qwen-backed rewrite path with the in-code `deterministic-graph-rewrite` engine.
- Removed bundled external Qwen model configs from the release path.
- Hardened graph validation and save behavior, so missing evidence, missing node references, and missing embeddings fail before graph JSON is written.
- Confirmed the same character knowledge graph can improve current character summary/backstory rewrites by feeding people, places, relationships, drives, and evidence into deterministic generated prose and the semantic improvement report.
- Disabled model-config-backed random character backstory generation for this release.
- Updated README, release notes, and rewrite design docs to reflect graph-backed generation instead of model downloads.
- Testing: run focused graph, rewrite, model-config, semantic-report, and character-generation tests before committing this section.

### Structured Knowledge View
- Lock down the current knowledge graph view under the name "Structured Knowledge View"
- Refactor the code base so new knowledge views can be created without breaking the existing view.
- Use the UI code that was formally used to display the full knowledge graph to test this out.

### Knowledge Graph UI Review And Detail Panel - 2026-07-18

- Pulled the latest remote `main` into `feature/knowledge_graph` before implementation.
- Captured the current Session Notes import graph screenshot at `docs/screenshots/Knowledge_Graph_current_2026-07-18.png`.
- Compared the current graph fidelity against `docs/screenshots/Knowledge_Graph.png` in `reports/knowledge_graph_report.md`.
- Combined `docs/specs/KNOWLEDGE_GRAPH_DESIGN2.md` into `docs/specs/KNOWLEDGE_GRAPH_DESIGN.md`.
- Removed the duplicate Combined Knowledge Graph heading from the Streamlit UI.
- Added a graph-node detail table below the combined graph chart.
- Updated `docs/reports/ui_issue_report.md`.

### Session Note Graph One-Screen Projection - 2026-07-18

- Limited session-note-derived combined graph data to internal evidence sources and extracted entity candidates instead of exposing the session-note source as a graph root.
- Reduced the raw `Session_Notes.txt` projection estimate from 24 visible nodes and 30 edges to 4 visible nodes and 3 edges.
- Added `docs/specs/KNOWLEDGE_GRAPH_DESIGN3.md` for the longer-term session-note extraction and review-table design.
- Verified with `.venv/bin/python -m pytest tests/test_combined_character_graph.py tests/test_character_graph.py`.

### Session Note Graph 2-3 Screen Recommendation Update - 2026-07-18

- Expanded the session-note graph target from one-screen pruning to a 2-3 screen projection for longer-running imported campaigns.
- Added session-note entity extraction for likely characters and places, with authored character sheets sorted before derived entities.
- Added one-paragraph main-character stubs for Vivit, Typhon, Dizlevad, Mog, and Flicker.
- Added `docs/reports/knowledge_graph_recommendation_update_report.md`.
- Verified with direct graph tracing and `.venv/bin/python -m pytest tests/test_combined_character_graph.py tests/test_character_graph.py`.
- Limited graph tabs to authored main characters and authored main places.
- Limited graph root selection to authored main characters and authored main places; session notes are retained only as internal evidence sources and never shown as graph roots.
- Added party-centered graph rendering that keeps all main characters in one vertical column and places outside-party connections in the next character/place columns.
- Added graph layout groups for Family Names, Party/Main Characters, Secondary Characters, and Places, verified against committed non-hidden fixtures and ordered by mention count where applicable.
- Kept source-file labels out of the graph DOT, with sources shown only in lower detail/list rows; the family-name column naturally renders empty when no family nodes exist.
- Added a full character connection graph mode button so the UI can switch back from the party-centered graph to the full non-session graph.
- Fixed old `.txt` session-note bulk imports by converting them to markdown files so the Session Notes UI and Combined Knowledge Graph can read them.
- Added a combined graph revision marker for UI lore writes, imports, deletes, restores, undo actions, and graph regenerations so graph widget state refreshes after file changes.
- Added an opt-in Playwright screenshot capture path for hidden lore fixtures.
- Added direct character graph generation coverage for every character sheet, including hidden lore when `LOCAL_CHATBOT_CHARACTER_GRAPH_TEST_LORE_DIR` is set.
- Added `docs/reports/knowledge_graph_fixed_issues_report.md` summarizing fixed knowledge graph issues.
- Replaced raw node source paths in graph evidence tables with compact source filename labels.

### Knowledge Graph Display Columns - 2026-07-19

- Added a Combined Knowledge Graph mode switch for `Single Character` and `Whole Graph`.
- Changed the single-character graph to show only connections associated with the selected graph node.
- Ordered graph roots, columns, and associated graph items by mention/evidence count before name tie-breakers.
- Collapsed duplicate graph edges to the most prominent relationship label shown between two nodes.
- Split relationship evidence into separate table rows instead of combining evidence into one joined cell.
- Removed Markdown bullet/list markers from evidence table display.
- Typed named session-note source nodes such as `Family Tree` as `source_document`, placing them in the Family Names column with a distinct graph shape instead of showing them as secondary characters.
- Labeled family-name graph nodes as `{Name} Family` and added `group` nodes such as `Ignis Cult` to the Family Names column with a distinct shape.
- Kept graph edge text on-line with normal `label` attributes and handled ambiguity through node spacing and target-column layout instead of floating head/tail labels.
- Moved non-main places into the secondary-character target column for focused/party graph layouts so connected target nodes stack vertically instead of drawing ambiguous arrows through each other.
- Made graph edge-label text theme-aware so light mode uses dark slate text and dark mode uses light text.
- Increased graph rank/node spacing so straight-line graph labels have more breathing room around their edges.
- Added wider small-graph spacing for focused graph views to reduce default label overlap around central character nodes.
- Reduced family/source-document icon dimensions in the left column and widened focused graph rank spacing to prevent oversized left-side icons from crowding the main character.
- Kept family-name nodes as ordinary ovals with modest dimensions and margins, avoiding the oversized regular-circle look.
- Fixed `Family Tree` only appearing for directly mentioned characters by deriving family-node links from family section headings and surfacing source documents connected through a character's family node.
- Normalized the `Nighbloom` family heading to the existing `Nightbloom Family` node and stripped Markdown heading markers from evidence display.
- Verified with `.venv/bin/python -m pytest -q tests/test_character_graph.py tests/test_combined_character_graph.py`.

### Completed - Graph JSON Saves And Character Form Improvements - 2026-07-19

- Pulled the latest `develop` branch from the `main` remote before implementation.
- Added graph JSON generation for place saves, session-note saves/imports, and bulk lore import/restore backfills.
- Changed the Combined Knowledge Graph loader to prefer saved graph JSON and regenerate missing JSON as a backfill.
- Preserved session-note `source_document` node type when duplicate loose import-source markdown has the same graph id.
- Made character display names editable and allowed new characters to be saved without Race or Class.
- Updated `docs/reports/ui_issue_report.md`.
- Verified with `.venv/bin/python -m pytest -q tests/test_entity_file_saves.py`, `.venv/bin/python -m pytest -q tests/test_session_notes.py tests/test_combined_character_graph.py tests/test_character_graph.py`, `.venv/bin/python -m pytest -q tests/e2e/test_session_notes_ui.py::test_ui_uploaded_session_note_updates_combined_graph_from_configured_notes_dir`, and `.venv/bin/python -m pytest -q tests/e2e/test_character_sheet_roundtrip_ui.py::test_create_validation_preserves_entered_fields`.
