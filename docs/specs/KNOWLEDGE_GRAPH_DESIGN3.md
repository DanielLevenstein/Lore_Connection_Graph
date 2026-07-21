# Knowledge Graph Design 3: Session Note Graph Fidelity

## Problem

The current combined knowledge graph can render imported session-note data, but the extraction quality is not good enough for a campaign-level graph. The UI issue report notes that the fresh `world_building/import/Session_Notes.txt` screenshot produces many visible low-value nodes from ordinary prose, including sentence fragments and common words. The graph is technically functional, but the user cannot trust the entity list.

This is an extraction and modeling issue first, and a UI issue second. Adding a detail table helps review a selected node, but it does not prevent false nodes from entering the chart.

## Best Direction

Separate session-note extraction from character-sheet extraction.

Character sheets are structured around one primary character. Session notes are chronological prose with many incidental mentions, actions, quoted speech, dates, places, jokes, spell names, and partial sentence fragments. Reusing the character extractor for session notes causes false positives because it assumes capitalized phrases are likely graph entities.

The best fix is a two-stage session-note graph pipeline:

1. Extract candidate facts into a review table.
2. Promote only validated people and places into the combined graph.

This keeps the combined graph strict while preserving potentially useful extracted details for review.

## Graphviz Default Options

| Area | Default | Reason |
| --- | --- | --- |
| Graph direction | `rankdir=LR` | Keeps the focused character graph readable as a left-to-right relationship map. |
| Background | `bgcolor="transparent"` | Lets the Streamlit theme show through without a boxed chart background. |
| Edge routing | `splines="line"` | Keeps labels visually attached to straight edges instead of drifting onto curved routing. |
| Node style | `style="rounded,filled"` | Matches the readable card-like node treatment in the liked character view. |
| Default node fill | `fillcolor="#dbeafe"` | Distinguishes normal character nodes from typed lore nodes. |
| Node outline | `color="#94a3b8"` | Gives visible boundaries without heavy contrast. |
| Node font | `fontname="Inter"`, `fontcolor="#000000"` | Keeps node labels stable and readable in Graphviz SVG output. |
| Default node shape | `shape="box"` | Keeps character nodes compact and easy to scan. |
| Edge color | `color="#64748b"` | Provides enough edge contrast without overpowering node labels. |
| Edge font | `fontname="Inter"`, `fontsize=10` | Keeps relationship labels compact enough to sit on edges. |
| Edge label color | `fontcolor` and `labelfontcolor` from the active theme | Keeps labels readable in light and dark mode. |
| Edge label placement | `label="Relationship"` | Places the relationship text on the associated edge path. |
| Endpoint labels | Avoid `headlabel` and `taillabel` by default | Endpoint labels looked less attached to their relationships in this UI. |
| Same-column edge constraints | `constraint="false"` only for same-column edges | Prevents intra-column relationships from breaking the intended column layout. |
| Broad-source fanout constraints | `constraint="false"` for broad-source vertical fanout edges | Lets vertical broad-source layouts stay readable when one source points to many targets. |
| Invisible column anchors | `style=invis`, `weight=100` between column anchors | Preserves the family/source, main character, secondary, and place column order. |
| Invisible intra-column stackers | `style=invis`, `weight=50`, `constraint="false"` | Stacks related nodes within a column without making those guide edges visible. |


### Typed Node Overrides

| Node type | Shape | Fill | Extra dimensions |
| --- | --- | --- | --- |
| Character | `box` | `#dbeafe` | None |
| Place | `component` | `#dcfce7` | None |
| Group | `trapezium` | `#e9d5ff` | None |
| Family | `ellipse` | `#fef3c7` | `width=1.9`, `height=0.8`, `margin="0.14,0.06"` |
| Source document | `folder` | `#fde68a` | `width=1.65`, `height=0.7`, `margin="0.12,0.06"` |

### Session Note Attribute Graph

Create a session-note-specific derived graph that stores reviewable facts without assuming they are global nodes.

Recommended row shape:

- `id`
- `source_file`
- `source_heading`
- `entity_name`
- `entity_type`
- `relationship_type`
- `related_entity_name`
- `related_entity_type`
- `description`
- `evidence`
- `confidence`
- `status`

`status` should support:

- `candidate`
- `accepted`
- `rejected`

Only `accepted` rows should become combined graph edges.

### Combined Graph Projection

The combined graph should remain a projection of trusted campaign entities:

- Character nodes from character sheets.
- Place nodes from place lore.
- Accepted people and places from session-note review rows.
- Explicit family nodes only when a character sheet or accepted row provides enough context.

The combined graph should not directly display:

- Pronouns.
- Spell names unless modeled as a future `Concept` node type.
- Common words.
- Partial sentence fragments.
- Dates or timestamps.
- Generic party references unless represented as a known faction/group.

## Extraction Rules

Session-note extraction should use stricter candidate gates:

- Require multi-token proper names unless the name already exists in known lore.
- Match candidates against existing character and place names before creating new nodes.
- Reject common stop words and dialogue fragments.
- Reject headings that are only dates, months, or session numbers.
- Preserve uncertain mentions as `candidate` rows rather than chart nodes.
- Limit evidence to one context-aware sentence or clause.

Known lore should act as the main authority. If `Jory Ravenmark` exists in character sheets, a session-note mention of `Jory` can link to that node. If `There` appears in prose, it should not become a new character.

## UI Design

The UI should expose three review surfaces:

- Combined graph chart: accepted people and places only.
- Selected node detail table: incoming and outgoing accepted edges for the current node.
- Extraction review table: candidate facts removed from the chart, with evidence and confidence.

The current node detail table is a good first step. The next UI improvement should be the extraction review table, not more visual decoration in the chart.

## Testing Plan

Add focused tests for `Session_Notes.txt` or a smaller representative fixture:

- The combined graph does not include common-word nodes such as `There`, `Did`, `You`, `Without`, or `Only`.
- Existing known character names are linked instead of duplicated.
- Rejected or candidate session-note facts remain available in a review table.
- Accepted rows project into the combined graph.
- The graph screenshot contains only recognizable people, places, or approved family/group nodes.
