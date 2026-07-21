# Combined Knowledge Graph

## Purpose

The combined knowledge graph is a campaign-level view built from authored lore in `world_building/lore`. It connects character sheets, place files, and secondary references into one navigable graph without requiring the player to manually load each character file.

## Source Of Truth

- `docs/` stores committed specifications, designs, templates, reports, and screenshots.
- `world_building/import` is the staging area for raw import files.
- `world_building/lore` is the canonical user-facing campaign Markdown store.
- `world_building/lore/character_sheets` is the source for available character sheets.
- `world_building/lore/places` is the source for available places.
- `world_building/lore` is ignored by git and should contain user-local campaign data.
- `world_building/meta_data/character_graph` stores derived per-character graph JSON and can be rebuilt.
- `world_building/meta_data/character_metadata` stores runtime profile metadata, memory notes, and chat logs.
- Generated characters are written to `world_building/lore/character_sheets` only after the player saves them.

## Visibility

Knowledge graph is now enabled by default, but was previously gated behind `LOCAL_CHATBOT_ENABLE_COMBINED_GRAPH`

## Inputs

When generating the combined graph, the app should parse all supported lore files under `world_building/lore`:

- `world_building/lore/character_sheets/*.md`
- `world_building/lore/character_sheets/*/BACKSTORY.md`
- `world_building/lore/places/*.md`

## Graph Semantics

- Authored character sheets become primary character nodes.
- Authored place files become place nodes.
- Secondary characters mentioned in sheets or places become character nodes even if no full sheet exists.
- Relationships sourced from other character sheets and places should be shown before relationships sourced from the current character's own sheet when appending `Character Connections`.
- Places should appear in the graph when they have at least one connection, even when they do not have a full character sheet associated with them.
- Self-referencing edges are invalid and must be dropped.
- Nodes with no remaining incoming or outgoing edges must be hidden from the combined graph UI.

## UI Requirements

- Each tab should show the graph for a different character or lore source.
- The UI should not require manual file loading.
- Players should be able to create new place and character files from secondary character/place nodes.
- Players should be able to append a `Character Connections` section to the bottom of an existing character sheet.

## Generation Rules

- Summary and backstory text may be generated from graph data only after an explicit player action.
- Auto-generated sections must include `Auto Generated` next to the markdown section title.
- Generated content should remain editable markdown and should not replace authored text silently.
