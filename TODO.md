# Change log
The changelog has been moved to the bottom of RELEASE_NOTES.md

# UI Bug Reports
- pull the latest changes from the main before writing code.
- Update `ui_issue_report.md` after UI bugs are fixed. 
- Remove graph-edge report grade from the UI.
- Newly created characters don't show up on the knowledge graph
- Imported session notes don't show up in the knowledge graph

## UI Improvements
- Make User Display Name Editable
- Allow saving users without defining class and race.

## Graph Improvements
- Set a max number of secondary places and characters and make it configurable.
- Identify why Justice and Night bloom are showing up in the knowledge graph even though they aren't characters or places.
- Don't render party - party connections in party view. It clutters up the UI. 
 
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

## Completed - Screenshot-Era Graph UI Restore - 2026-07-19

- Restored the old Combined Knowledge Graph UI shape directly for verification.
- Split the graph controls into `Single Character View`, `Test Fixture`, and `Full Structured Graph`.
- Marked `Test Fixture` as the screenshot-target renderer for `Structured_Knowledge_Graph_Full.png`.
- Added `docs/reports/knowledge_graph_migration_path.md` for moving from fixture parity to the current full structured graph.
- Reconnected secondary character/place curation controls under the character-focused graph view.
- Deferred compatibility with the newer party/full split until the restored path is verified.
