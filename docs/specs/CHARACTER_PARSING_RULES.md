# Character Parsing Rules

Character sheets are authored markdown files stored in `world_building/lore/character_sheets`.
This directory is ignored by git so each user can keep their own campaign lore local.

`world_building/lore/character_sheets` is the source of truth for editable character Markdown. Runtime metadata derived from those files belongs under `meta_data/character_metadata`, and generated graph JSON belongs under `meta_data/character_graph`.

## Supported Paths

- `world_building/lore/character_sheets/character_name.md`
- `world_building/lore/character_sheets/character_name/BACKSTORY.md`

## Required Sections

- H1 character name.
- `Character Stats` markdown table.
- `Character Backstory`.
- `Character Summary`, or a short summary directly under the H1 before the first `##` section.

## Save Rules

- Do not modify a character sheet unless necessary.
- When saving an existing sheet, update only the changed sections.
- Preserve custom stat headings and section headings in `PROFILE.json` aliases.
- If any name field exists in the stats table, display it exactly as written.
- Default stat fields are `Name`, `Level`, `Race`, `Class`, and `Pronouns`.
- Add missing default stat columns only when the profile has a value to save.
- Mirror custom stat columns into `Character Details` for UI editing.
- Support first-name-only characters without inventing a family name.

## Generated Sections

- Graph-derived summary or backstory text is generated only when the player clicks an explicit UI action.
- Generated markdown headings include `(Auto Generated)`.
- Generated sections remain normal editable markdown after creation.

## Character Connections

`Character Connections` may appear as a top-level section or as a subsection appended below `Character Summary`. The parser reads table rows into `knowledge_graph_fields` in the character profile JSON.
