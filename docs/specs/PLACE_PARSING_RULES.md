# Place Parsing Rules

Places are authored markdown files stored in `data/lore/places`.

## Supported Format

Each place file should use this shape:

```markdown
# Place Name

## Place Stats

| Name | Type |
| ---- | ---- |
| Royal Tittles | Tavern |

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
- Files in `data/lore/places` are player-authored source files and should stay local because `data/lore/` is ignored by git.
- Generated or derived graph JSON remains under `data/` and can be rebuilt.
