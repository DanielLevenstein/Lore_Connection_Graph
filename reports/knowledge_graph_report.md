# Knowledge Graph UI Fidelity Report

Date: 2026-07-18

## Inputs Reviewed

- Current behavior screenshot: `docs/screenshots/Knowledge_Graph_current_2026-07-18.png`
- Reference screenshot: `docs/screenshots/Knowledge_Graph.png`
- Test import: `world_building/import/Session_Notes.txt`

The current screenshot was captured from an isolated Streamlit run with `LOCAL_CHATBOT_ENABLE_COMBINED_GRAPH=1` after importing `Session_Notes.txt` through the Session Notes upload flow.

## Current UI Strengths

- The import flow can ingest the large session-note text file and still render the combined knowledge graph without crashing.
- The combined graph keeps a reviewable relationship table below the visualization.
- The graph builder prunes disconnected nodes, so not every extracted token reaches the visible chart.
- The UI preserves evidence text, which is essential for deciding whether a relationship should be kept, edited, or discarded.

## Fidelity Compared With `Knowledge_Graph.png`

The reference screenshot shows a relatively legible graph centered on recognizable lore entities: named characters, family nodes, and places such as Sunstone Mage College. The current session-note import produces a much noisier graph. In the captured run, extraction produced 24 visible combined nodes and 30 combined edges, including low-value nodes such as `There`, `Did`, `You`, `Without`, and `Only`.

The biggest fidelity gap is entity quality, not rendering. The chart can draw the graph, but the extractor currently treats sentence fragments and common words as candidate characters when session notes are used as graph input. This makes the graph look dense while reducing trust in the visible relationships.

## Improvements Made

- Removed the duplicate top-level `Combined Knowledge Graph` heading so the graph section begins with the existing expander title.
- Added a `Graph Node` selector and node detail table below the graph. The table shows the selected node, incoming edges, outgoing edges, relationship labels, connected node types, and evidence.
- Folded `KNOWLEDGE_GRAPH_DESIGN2.md` into `KNOWLEDGE_GRAPH_DESIGN.md` so the redesign requirements live in one spec.
- Reduced the visible graph projection for session-note imports to the session-note source plus extracted places. The raw `Session_Notes.txt` extraction still produces 52 candidate character nodes and 54 relationships, but the visible combined graph now projects to 4 nodes and 3 edges: `Session Notes`, `Pixie Kingdom`, `Forest`, and `Hall`.

## One-Screen Size Estimate

No new browser screenshot was captured for this pass. Estimating from the raw post-fix graph shape, 4 visible nodes and 3 edges should fit comfortably on one desktop screen. The previous 24-node, 30-edge projection was too wide and noisy; the new projection is a compact source-to-place diagram.

## Recommended Next Improvements

- Add session-note-specific extraction rules so imported notes do not use character-sheet heuristics blindly.
- Filter candidate nodes with a stricter person/place classifier before they enter the combined graph.
- Add a low-confidence review table for extracted details that are intentionally omitted from the chart.
- Replace the static Graphviz chart with an interactive graph component if true node-click events become a priority.
- Keep the combined graph focused on campaign navigation: named people, places, and explicitly meaningful family nodes only.

## Verification Targets

- Unit tests should validate node detail table rows for incoming and outgoing relationships.
- Playwright tests should assert that the combined graph exposes the `Graph Node` selector and detail table after the graph expander opens.
- Future visual QA should compare session-note imports against known-good screenshots and flag common-word nodes.
