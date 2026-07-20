
# feature/knowledge_graph

## 2026-07-18

### Knowledge Graph UI Review And Detail Panel
- Added the graph-node detail table, removed the duplicate Combined Knowledge Graph heading, and merged the v2 design notes into the main knowledge graph design document.

### Session Note Graph Projection
- Reworked session-note graph extraction around internal evidence sources, authored entities, and a 2-3 screen graph target for larger imported campaigns.

### Party-Centered Graph Layout
- Added party-centered rendering with authored main characters and places as graph roots, family/group/source columns, compact source labels, and refreshed graph state after lore changes.

# develop

## 2026-07-19

### Graph JSON Saves And Character Form Improvements
- Added graph JSON save/backfill paths for places, session notes, imports, and restores, while making character display names editable and allowing saves without Race or Class.

### UI Validation Follow-Up
- Added Playwright coverage for minimal character creation appearing in the graph, fixed repeated character undo state, and confirmed graph clarity grades stay out of the UI.

# feature/knowledge_graph2

## 2026-07-19

### Knowledge Graph Display Columns
- Added focused and whole-graph display modes with ordered columns, de-duplicated relationship labels, cleaner evidence rows, family/group source handling, and theme-aware graph text.

### Screenshot-Era Graph UI Restore
- Restored the screenshot-era Combined Knowledge Graph UI for verification, added the migration path report, and reintroduced the temporary structured graph comparison view.

### Broad Knowledge Graph Source Filtering
- Treated place-lore roots as source-document provenance, hid source-document knots from broad graph views, and preserved matching extracted places as entity nodes.

## 2026-07-20

### Graph Rendering Refactor
- Moved Streamlit knowledge graph rendering into `graphviz_rendering.py`, split graph rendering by top-level knowledge tabs, and locked the existing full renderer behind `Structured Knowledge View`.

### Place And Session Lore Graphs
- Added Place Lore and Session Notes lore graph layouts with source/group columns, Markdown H1-H3 heading columns, place and character connection columns, hidden empty headings, straight-line edges, and connection-count sorting.

### Secondary Entity Creation Removal
- Removed graph-based secondary character/place creation controls, draft state, and unused stub creation helpers, with e2e coverage to keep those controls absent.

### Graph View Defaults And Fixtures
- Defaulted the Places tab to the place-lore view, renamed the party fixture config, and added six dedicated graph-view fixture JSON files for screenshot coverage.

### Graph Screenshot Coverage
- Added an end-to-end screenshot test for Characters `Single Character` and `Party View`, Places `Place Lore` and `Party View`, and Session Notes `Place Lore` and `Party View`, with distinct output filenames.

### Lore Connection Tables
- Limited lore-view connection tables to rows with character connections, so non-character heading and document edges stay out of the table.
