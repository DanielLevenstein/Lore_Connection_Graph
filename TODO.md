# UI Bug Reports
- pull the latest changes from the main before writing code.
- Update `ui_issue_report.md` after UI bugs are fixed. 

## Session Planing
1) Get new screenshot of the existing behavior with the following test data `world_building/import/Session_Notes.txt`
2) Compare the fidelity of the extracted knowledge graph to the existing file in `docs/screenshots/Knowledge_Graph.png`
3) Write out a report under `reports/knowledge_graph_report.md` indicating what the current UI does well and how it can be improved.
4) Review KNOWLEDGE_GRAPH_DESIGN.md and KNOWLEDGE_GRAPH_DESIGN2.md combine files into a single document.
5) When UI bugs related to the knowledge graph functionality are fixed `update ui_issue_report.md` 

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

## Character Rewrite Improvements

### Goals

- Generate character summaries and backstories from the character graph instead of deterministic fallback prose.
- Let missing character graphs be regenerated automatically before rewrite actions.
- Avoid requiring a long-running local API server for one-off rewrite generation.
- Show visible feedback when a local model artifact needs to be downloaded.
- Compare generated, existing, and original backstory sections in the semantic improvement report.

### Character Rewrite Metadata Stabilization

- Centralized deterministic rewrite story signals so summary, backstory, prompt context, and required-term scoring use the same profile-plus-graph facts.
- Preserved JSON/metadata-backed origin, drives, alliances, enemies, motivations, custom stat fields, and source-backed places in rewrite scoring and generated prose.
- Filtered non-story attribute artifacts out of relationship prose, so race, class, family placeholders, and place edges do not masquerade as character relationships.
- Regenerated `docs/reports/semantic_backstory_improvement.md` with model, existing generated, and original backstory scores.
- Testing: `.venv/bin/python -m pytest tests/test_semantic_improvement_report.py tests/test_character_rewrite_model_lifecycle.py tests/e2e/test_character_rewrites.py`; `.venv/bin/python -m pytest tests/test_semantic_improvement_report.py tests/test_character_rewrite_model_lifecycle.py tests/test_character_graph.py tests/test_model_downloads.py tests/test_character_generation.py`.
