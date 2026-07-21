# Knowledge Graph Migration Path

Date: 2026-07-19
Branch: experiment/Structured_Graph_Retreval

## Current Finding

`Structured_Knowledge_Graph_Full.png` matches the character-sheet-only fixture subset, not the full current lore set.

The fixture subset is:

- `tests/fixtures/character_sheets/Jory_Ravenmark.md`
- `tests/fixtures/character_sheets/Neal_Lovington.md`
- `tests/fixtures/character_sheets/Orin_Nightbloom.md`

It excludes:

- `tests/fixtures/places/Atlantia_Lore.md`
- `tests/fixtures/session_notes/Family_Tree.md`

## View Roles

- `Single Character`: focused node graph for one selected main character or place.
- `Character Data Only`: character-sheet-only graph path for preserving the screenshot-era baseline. This is implemented by the internal `party_view_fixture` view key because it identifies the fixture source without bringing back the old Party View.

## Migration Steps

1. Keep `Character Data Only` as the locked baseline until `Structured_Knowledge_Graph_Full.png` can be reproduced through the normal UI.
2. Compare `Character Data Only`, `Place Graph`, `Session Note Graph`, node sets from the same lore directory and classify added nodes as desired, noisy, or duplicate.
3. Promote desired place/session-note nodes into stable typed categories instead of allowing them to appear as accidental secondary characters.
4. Add regression coverage for the accepted full structured node set, then regenerate the full structured screenshot under a new screenshot name.
5. After the full graph is stable, decide whether `Character Data Only` remains as a diagnostic view or moves behind an e2e-only flag.

## Immediate Next Check

Run the app with current lore and compare:

- `Character Data Only`: should show only character-sheet-derived nodes.
- `Place Graph`: should show source documents, place names, and character connections from place lore.
- `Session Note Graph`: should show dates, characters, and places from selected session-note months.
