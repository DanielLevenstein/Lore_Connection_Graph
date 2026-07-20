# Node Deduplication Design

## Purpose

Node deduplication is a review workflow for cleaning duplicate, noisy, or incorrectly typed knowledge graph nodes without directly editing generated graph JSON. Authored lore remains the source of truth; deduplication decisions are saved as review rules that can be reapplied when graphs are regenerated.

## Views

### Character Deduplication
- Shows likely duplicate character nodes grouped by normalized name, source evidence, and shared connections.
- Lets the user choose a canonical character node and mark aliases such as spelling variants, titles, or partial names.
- Keeps the selected canonical node visible in graph views while alias nodes collapse into it for display and connection tables.

### Place Deduplication
- Shows likely duplicate place nodes grouped by normalized name, markdown source, and nearby heading context.
- Lets the user choose a canonical place node and attach aliases from lore headings, source document names, or extracted references.
- Keeps place aliases from creating separate graph columns when they point to the same authored or reviewed place.

### Node Removal
- Shows low-confidence nodes that are neither accepted characters nor accepted places.
- Lets the user hide noisy entities from graph rendering while preserving the original evidence for later review.
- Supports restoring removed nodes if later lore or manual review confirms the node is meaningful.

## Layout

Deduplication views should use a freeform review graph with source documents and markdown headings hidden. The graph should emphasize candidate duplicates, accepted canonical nodes, and shared character/place relationships rather than reproducing the full lore outline.

Recommended columns for the review table:

- Candidate Node
- Suggested Type
- Matched Canonical Node
- Evidence Count
- Shared Connections
- Source Documents
- Review Action

## Matching Signals

The first pass should be deterministic and explainable:

- Case-insensitive normalized name match.
- Punctuation, apostrophe, and whitespace normalization.
- Singular/plural normalization for obvious group names.
- Shared source document or nearest markdown heading.
- Shared connected characters, places, or groups.
- Disallow-list hits such as `Family`, `Stone`, and `Students`.

Future semantic matching can suggest candidates, but it should not automatically merge nodes without review.

## Review Rules

Review decisions should be stored separately from generated graph JSON:

- `alias`: collapse candidate node into canonical node.
- `hide`: remove candidate node from rendered graphs and connection tables.
- `accept`: mark candidate node as a real character, place, or group.
- `restore`: undo a previous hide or alias decision.

Rules should include the reviewed node id, canonical node id when applicable, reviewer action, timestamp, source evidence, and a short reason. Regenerating graph JSON should reapply rules after extraction and before UI rendering.

## Testing

- Unit tests should verify that aliases collapse duplicate nodes without losing evidence rows.
- Unit tests should verify hidden nodes are removed from graph DOT and connection tables.
- E2E tests should cover one character merge, one place merge, and one node removal.
- Screenshot coverage should capture all three review views after a seeded fixture creates duplicate candidates.
