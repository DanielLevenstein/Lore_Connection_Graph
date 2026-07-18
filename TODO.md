# UI Bug Reports
- pull the latest changes from the main before writing code.
- Update `ui_issue_report.md` after UI bugs are fixed. 

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

### Bug Fixes
- Remove the headings at the top of the knowledge graph page. They don't currently affect the UI, and they clutter up the UI.
### Improvements
- When clicking on a specific node in the graph, populate a table below the graph with detailed info about that node. 
- Move the knowledge graph into a dedicated tab next to session notes

## Completed

### Knowledge Graph UI Review And Detail Panel - 2026-07-18

- Pulled the latest remote `main` into `feature/knowledge_graph` before implementation.
- Captured the current Session Notes import graph screenshot at `docs/screenshots/Knowledge_Graph_current_2026-07-18.png`.
- Compared the current graph fidelity against `docs/screenshots/Knowledge_Graph.png` in `reports/knowledge_graph_report.md`.
- Combined `docs/specs/KNOWLEDGE_GRAPH_DESIGN2.md` into `docs/specs/KNOWLEDGE_GRAPH_DESIGN.md`.
- Removed the duplicate Combined Knowledge Graph heading from the Streamlit UI.
- Added a graph-node detail table below the combined graph chart.
- Updated `docs/reports/ui_issue_report.md`.

### Session Note Graph One-Screen Projection - 2026-07-18

- Limited session-note-derived visible combined graphs to the session-note source and extracted place nodes.
- Reduced the raw `Session_Notes.txt` projection estimate from 24 visible nodes and 30 edges to 4 visible nodes and 3 edges.
- Added `docs/specs/KNOWLEDGE_GRAPH_DESIGN3.md` for the longer-term session-note extraction and review-table design.
- Verified with `.venv/bin/python -m pytest tests/test_combined_character_graph.py tests/test_character_graph.py`.
