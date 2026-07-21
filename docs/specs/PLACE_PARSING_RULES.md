# Place Parsing Rules

Places are authored markdown files stored in `world_building/lore/places`.

`world_building/lore/places` is the source of truth for editable place Markdown. Raw files to be imported should stay under `world_building/import`, and derived graph/runtime data belongs under `world_building/meta_data`.

## Supported Format

Each place file should use this shape:

```markdown
# Place Name

## Place Stats

| Name | Type |
| ---- | ---- |
| Royal Commons | Tavern |

## Place Summary

Short prose summary.

## Place Details

Freeform details.

## Place Connections

- Neal Lovington: Performs here.
```

## Rules

- The H1 is the canonical place name.
- `Place Stats` stores normalized fields, beginning with `Name` and `Type`.
- `Place Summary` is the short description used by graph generation.
- `Place Details` is freeform prose or tables.
- `Place Connections` is a bullet list of character, place, faction, or object references.
- Files in `world_building/lore/places` are player-authored source files and should stay local because `world_building/` is ignored by git.
- Generated or derived graph JSON remains under `world_building/meta_data/` and can be rebuilt.
