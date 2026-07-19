# Knowledge Graph Recommendation Update Report

Date: 2026-07-18

## Summary

The graph has been updated from a strict one-screen session-note projection to a 2-3 screen projection. This better matches the imported campaign's longer play history while keeping the graph bounded enough to review.

The current implementation now:

- Extracts likely character and place entities from session notes and place lore.
- Promotes known authored character names before derived names.
- Displays only authored main characters and authored main places as graph UI tabs and graph roots.
- Keeps `Session Notes` out of the graph view entirely; session-note files remain internal evidence sources for connections.
- Renders a party-centered graph from the selected tab or graph node, keeping all main characters visible together instead of leaving every tab on the same unfocused full graph or showing `Session Notes -> Selected Entity`.
- Records a graph clarity metric in reports and tests, without showing graph grades in the UI.
- Uses a party-centered graph structure: Family Names, Party/Main Characters, Secondary Characters, and Places.
- Keeps all main characters in the same vertical party column, with outside-party connections in the next character/place columns ordered by mention count.
- Restores a full non-session character connection graph mode for broader inspection.
- Converts old `.txt` session-note bulk imports to markdown so imported notes update the Combined Knowledge Graph.
- Marks the combined graph dirty after UI lore file changes so graph controls refresh on the next rerun.
- Lets the Family Names column render empty when no family nodes exist, without adding a UI toggle.
- Keeps source-file labels out of the graph DOT and shows them only in lower detail/list rows.
- Keeps broad session-note graphs in a vertical DOT layout instead of compressing them into a single wide row.
- Adds one-paragraph main-character stub sheets for Vivit, Typhon, Dizlevad, Mog, and Flicker.

## Direct Graph Trace

Verification used direct graph tracing rather than screenshot-based end-to-end tests. The layout contract is now tested against committed non-hidden fixtures instead of hidden session-note data.

Trace target: `world_building/lore`

Current traced graph:

| Metric | Value |
| --- | ---: |
| Authored character files | 5 |
| Authored place files | 0 |
| Derived relationships | 375 |
| Internal traced nodes | 28 |
| Internal traced edges | 28 |
| Graph view root nodes | 5 |
| DOT layout | vertical `rankdir=TB` |
| Non-constraining broad-source edges | 28 |
| Invisible layout guide edges | 26 |
| Dizlevad focused nodes | 8 |
| Dizlevad focused edges | 7 |

The report uses these full-graph numbers as the `Before Selection` clarity baseline, then grades the focused selected graph separately. The Streamlit UI intentionally does not display graph grades; selecting Dizlevad keeps the visible graph focused on a recurring main character instead of a one-session guest. The current direct trace finds seven actual Dizlevad connections: Flicker, Mog, Morningstar, Saraphen, Typhon, Vivit, and Feasting Orchard.

Graph view root nodes:

1. Dizlevad
2. Flicker
3. Mog
4. Typhon
5. Vivit

Internal traced character nodes, used for evidence and associated connections but not as roots unless promoted into authored lore:

1. Morningstar
2. Crotheise
3. John Doctor
4. Sachill
5. Sauriv
6. Tharevon
7. Elphira
8. Bloodmane
9. Cory
10. Mr Light
11. Saraphen
12. Trixie

Internal traced place nodes, used for associated connections but not as roots unless promoted into authored lore:

1. Pixie Kingdom
2. Feywild
3. Mentha
4. Big Top
5. Feasting Orchard
6. Witchlight Carnival
7. Forest
8. Pinewilds
9. Craigwood

## Coverage Change

The prior one-screen graph from `docs/reports/knowledge_graph_detail_report.md` showed only `Session Notes`, `Pixie Kingdom`, `Forest`, and `Hall`. That made it readable, but not useful enough during play.

Using the expected session-note entity list from that report:

| Entity group | Prior graph | Current graph |
| --- | ---: | ---: |
| Expected characters | 0 / 32, 0.0% | 18 / 32, 56.3% |
| Expected places, strict | 1 / 21, 4.8% | 8 / 21, 38.1% |
| Expected places, generous | 3 / 21, 14.3% | 10 / 21, 47.6% |
| Overall strict | 1 / 53, 1.9% | 26 / 53, 49.1% |
| Overall generous | 3 / 53, 5.7% | 28 / 53, 52.8% |

The current graph is meaningfully more useful for actual table reference because the party, major recurring NPCs, and key locations are present together. It is no longer a single-screen summary, but the added size buys back campaign memory.

## Main Character Coverage

The recurring main characters are now represented by authored stub sheets:

| Main character | Authored sheet | Visible in graph |
| --- | --- | --- |
| Vivit | Yes | Yes |
| Typhon | Yes | Yes |
| Dizlevad | Yes | Yes |
| Mog | Yes | Yes |
| Flicker | Yes | Yes |

Main-character coverage is **5 / 5, 100%**. Bosley the Beastly and Delia are intentionally not treated as main-character tabs for this screenshot pass.

## What Improved

The biggest improvement is that the graph now favors entities that can become real lore records. Authored character sheets are treated as stronger signals than raw capitalization, then the session-note extractor fills in major NPCs and places from repeated mentions.

The vertical layout also better matches the shape of imported notes. A long-running campaign produces a broad source hub, so the graph needs more vertical browsing space instead of trying to fit every important node into one compressed row.

## Remaining Gaps

The extraction pass is still heuristic. It handles common aliases such as Typhon spellings, Dizlevad, Sauriv, and John Doctor, but it does not yet provide a review workflow where the user can accept, reject, merge, or reclassify extracted names.

Relationship labels are still generic for derived session-note entities: `Mentioned` for characters and `Location` for places. The next useful improvement is to derive labels that explain why an entity matters, such as `party member`, `rescued`, `warned`, `visited`, `threatened`, or `investigated`.

Factions and threats remain intentionally conservative. Names like cults, monsters, and planar threats should become visible only after the graph has a faction or threat node type, otherwise the character graph starts mixing story actors with encounter categories.

## Recommendation

Continue with the 2-3 screen pruning target for focused views. Keep authored character and place files as the only graph roots, then promote validated session-note entities into authored lore before letting them become roots. Add a review table before expanding the graph much further, because human validation will do more for campaign usefulness than simply increasing node caps.
