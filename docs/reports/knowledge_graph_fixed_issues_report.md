# Knowledge Graph Fixed Issues Report

Date: 2026-07-18

## Summary

The Combined Knowledge Graph is now meaningfully interactive and better scoped for campaign use. The graph no longer treats every extracted session-note mention as a main navigation heading, and selecting a graph tab or root node now changes the rendered graph instead of leaving the same full graph on screen.

Updated screenshot:

- `docs/screenshots/Knowledge_Graph_From_Session_Notes.png`

## Issues Fixed

### Non-functional graph headings

Problem:

- The graph tabs looked like navigation headings, but every tab rendered the same full graph.
- This made the headings feel broken because selecting a character did not visibly focus the graph.

Fix:

- Graph tabs now render a focused summary graph for the selected main character or place.
- Graph roots are limited to authored main characters and authored main places.
- `Session Notes` is retained only as an internal evidence source and is not displayed as a graph root.
- The graph view draws the selected entity to actual associated people and places instead of showing `Session Notes -> Selected Entity`.
- Associated people and places are also listed in an `Other Connections` table below the graph; `Other Connections` is not rendered as a graph node.
- Repeated evidence for the same associated connection is split into separate `Other Connections` table rows.
- The selected node is highlighted in the DOT graph.
- The detail table below the graph now matches the selected graph node.
- Graph DOT output now follows a party-centered column structure: Family Names, Party/Main Characters, Secondary Characters, and Places.
- All main characters are forced into the same vertical party column.
- Connections outside the party are placed in the Secondary Characters and Places columns and ordered by evidence mention count.
- Relationship edges are non-constraining in column layout mode, leaving invisible column guides in control of placement.
- The UI includes a `Show Full Character Connection Graph` button to restore the full non-session graph view when the party-centered view is too narrow.
- The layout is covered by committed non-hidden fixtures instead of hidden session-note data.

### Too many graph tabs

Problem:

- Derived session-note mentions were shown as graph tabs.
- One-session or secondary entities could appear next to true main characters, which made the UI noisy and misleading.

Fix:

- Tabs and graph root selection are limited to authored main character sheets and authored main places.
- Derived characters and places can still appear as associated connections, but they are not selectable graph roots until promoted into authored lore.
- `Session Notes` is no longer offered as a secondary character file candidate.
- Bosley the Beastly was removed from the local main-character stub set because she was a one-session character and a poor test case for main-character behavior.

### Missing graph clarity feedback

Problem:

- The project had no recorded way to judge whether a graph became more readable after selecting a specific node.

Fix:

- Added a graph clarity metric to the markdown reports and direct graph tests.
- The metric reports grade, score, node count, edge count, max outgoing edges, and density in reports only.
- The Streamlit UI does not display graph grades or clarity scores.

### Screenshot path needed hidden/customer fixtures

Problem:

- The Playwright screenshot path needed to run against hidden/customer lore without committing that data.

Fix:

- Added `LOCAL_CHATBOT_E2E_LORE_FIXTURE_DIR` so the e2e fixture can copy a hidden lore directory into a temporary test world.
- Added `LOCAL_CHATBOT_E2E_KNOWLEDGE_GRAPH_SCREENSHOT` so screenshot writing is opt-in.
- The screenshot test is skipped by default when the screenshot env var is not set.

### Raw filesystem paths in node evidence

Problem:

- The node detail table exposed raw filesystem paths in the Evidence column.
- In screenshot runs this could leak temporary fixture directories or local workspace paths.

Fix:

- Node rows now show a compact source label such as `Source: Dizlevad.md`.
- Relationship evidence still shows prose evidence, not file paths.
- Added direct graph coverage so node detail evidence cannot regress to a raw path with slash-separated directories.
- Source labels are shown only in the lower `Extended Notes` detail/list section, not in the graph DOT.

### Family names needed optional layout handling

Problem:

- Family nodes help orient the graph, but they are not guaranteed to exist for every focused view.

Fix:

- The column layout keeps a stable Family Names column.
- When no family nodes exist in a focused graph, the Family Names column renders empty without requiring a checkbox.
- Family source/detail information remains available in the lower detail section when family nodes are present.

### Selected character connections were undercounted

Problem:

- Hiding the `Session Notes` hub initially made Dizlevad appear to have only one visible connection.
- Canonicalized typo variants such as `Dizelvad`, `Typhin`, and `Typhen` were counted into the right nodes, but the focused graph did not use those variants when tracing evidence-backed co-mentions.

Fix:

- Session-note extraction now keeps sentence-level evidence internally instead of a single joined evidence blob.
- Focused graph tracing recognizes canonical session-note name variants and filters displayed evidence to snippets that mention the selected node.
- Honorific-only aliases such as `Mr` are no longer treated as useful evidence matches.
- Direct graph tracing now shows Dizlevad connected to seven actual people/places in the hidden lore trace: Flicker, Mog, Morningstar, Saraphen, Typhon, Vivit, and Feasting Orchard.

### Character graph generation coverage was incomplete

Problem:

- Tests did not generate character graphs for every available character sheet.
- This missed graph validation issues such as empty-evidence place relationships.

Fix:

- Added `test_generates_valid_character_graphs_for_all_character_sheets`.
- By default it validates every committed fixture character sheet.
- With `LOCAL_CHATBOT_CHARACTER_GRAPH_TEST_LORE_DIR`, it validates every hidden/customer character sheet.
- Hardened place extraction so generic one-word place category labels such as `School` do not become empty-evidence place nodes.

### Imported old session notes did not refresh the graph

Problem:

- Bulk lore import only copied markdown files from `session_notes`.
- Older imports such as `Session_Notes.txt` were skipped or left outside the markdown-based Session Notes and Combined Graph scanners.
- UI file writes did not share one explicit graph-refresh signal.

Fix:

- Bulk lore import now accepts `.txt` files for session notes and writes them as `.md`.
- UI lore creates, edits, imports, restores, deletes, undo actions, and graph regenerations bump a combined graph revision marker before rerun.
- The graph root selector key includes that revision, preventing stale selector state after file changes.
- Added direct import coverage for `Session_Notes.txt -> Session_Notes.md`.

## Current Main Tabs

The current hidden-lore screenshot shows these main-character tabs:

1. Dizlevad
2. Flicker
3. Mog
4. Typhon
5. Vivit

Bosley the Beastly and Delia are intentionally absent from the main tabs.

`Session Notes` is intentionally absent from both the main tabs and graph root selector.

## Verification

Default direct graph and screenshot-skip verification:

```bash
../.venv/bin/python -m pytest tests/test_character_graph.py tests/test_combined_character_graph.py tests/e2e/test_character_sheet_roundtrip_ui.py::test_capture_knowledge_graph_screenshot -q
```

Result:

- `51 passed, 1 skipped`

Hidden-lore all-character graph generation:

```bash
LOCAL_CHATBOT_CHARACTER_GRAPH_TEST_LORE_DIR=/Users/daniel/Projects/Chatbot_Harness/Lore_Connection_Graph/world_building/lore \
../.venv/bin/python -m pytest tests/test_character_graph.py::test_generates_valid_character_graphs_for_all_character_sheets -q
```

Result:

- `1 passed`

Opt-in screenshot capture:

```bash
LOCAL_CHATBOT_E2E_LORE_FIXTURE_DIR=/Users/daniel/Projects/Chatbot_Harness/Lore_Connection_Graph/world_building/lore \
LOCAL_CHATBOT_E2E_KNOWLEDGE_GRAPH_SCREENSHOT=/Users/daniel/Projects/Chatbot_Harness/Lore_Connection_Graph/docs/screenshots/Knowledge_Graph_From_Session_Notes.png \
../.venv/bin/python -m pytest tests/e2e/test_character_sheet_roundtrip_ui.py::test_capture_knowledge_graph_screenshot -q
```

Result:

- `1 passed`

## Remaining Work

- Relationship labels for derived session-note entities are still generic: mostly `Mentioned` and `Location`.
- A review workflow is still needed for accepting, rejecting, merging, or reclassifying extracted entities.
- Factions and threats should remain out of the main graph until the graph has explicit faction or threat node types.
