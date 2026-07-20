# TODO

## Completed - Screenshot Fixture Cleanup And Deduplication Design - 2026-07-20 - feature/knowledge_graph2
- Fixed graph-view screenshot capture so e2e screenshots are less likely to be cut off.
- Removed committed graph-view JSON fixtures so screenshot coverage depends on the ingestion workflow.
- Added a synthetic multi-session Discord-style session-note fixture for import tests, starting at Session 1.
- Added Place and Session Note `File View` and `Session View` filters for source files and Markdown headings, including linked-character fan-out from file roots.
- Removed unlisted `Place Lore` and `Session Lore` tabs from the visible Places and Session Notes graph views.
- Deprecated obsolete Place/Session graph screenshots that no longer map to active UI views.
- Added the node deduplication design doc.
- Updated the changelog summary.
- Cleaned session-note evidence table text so Markdown fragments, table rows, underscored names, and model-polished evidence render as grammatical human-readable sentences.
- Kept semantic place/group headings in their Markdown heading columns with place/group icon styling, fanned place headings out to character connections, and added non-graph lore summary rows for descriptive headings.
