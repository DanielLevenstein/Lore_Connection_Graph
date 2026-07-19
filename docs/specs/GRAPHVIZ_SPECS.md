# Graphviz Specs

These defaults capture the Graphviz options that have worked well for the character-specific `Single Character View`. Keep this as the baseline before changing the full graph layout.

Editable defaults live under `config/graphviz/`. Global defaults are applied first from `config/graphviz/global_graph_view.json`, then each knowledge view applies its own override file such as `config/graphviz/character_view.json` or `config/graphviz/full_structured_graph.json`.

## Character-Specific View Defaults

| Area | Default | Reason |
| --- | --- | --- |
| Graph direction | `rankdir=LR` | Keeps the focused character graph readable as a left-to-right relationship map. |
| Background | `bgcolor="transparent"` | Lets the Streamlit theme show through without a boxed chart background. |
| Edge routing | `splines="line"` | Keeps labels visually attached to straight edges instead of drifting onto curved routing. |
| Small graph spacing | `ranksep=1.15`, `nodesep=0.4` | Gives focused graphs enough label breathing room around the central node. |
| Column/fuller graph spacing | `ranksep=0.65`, `nodesep=0.35` | Keeps larger column layouts compact while preserving label legibility. |
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

## Typed Node Overrides

| Node type | Shape | Fill | Extra dimensions |
| --- | --- | --- | --- |
| Character | `box` | `#dbeafe` | None |
| Place | `component` | `#dcfce7` | None |
| Group | `trapezium` | `#e9d5ff` | None |
| Family | `ellipse` | `#fef3c7` | `width=1.9`, `height=0.8`, `margin="0.14,0.06"` |
| Source document | `folder` | `#fde68a` | `width=1.65`, `height=0.7`, `margin="0.12,0.06"` |

## Regression Expectations

- Graph labels should be measured from the rendered SVG, not judged from screenshots alone.
- Every edge label should be asserted against the `g.edge` group that owns it.
- The screenshot artifact for the full graph regression should be `docs/screenshots/Structured_Knowledge_Graph_Full.png`.
- Full-graph layout changes should preserve the character-specific defaults unless the regression proves a different option keeps labels more tightly associated with their edges.
