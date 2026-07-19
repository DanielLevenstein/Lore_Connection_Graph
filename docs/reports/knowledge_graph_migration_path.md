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

- `Single Character View`: focused node graph for one selected main character or place.
- `Test Fixture`: character-sheet-only graph path for preserving the screenshot-era baseline.
- `Full Structured Graph`: current unfiltered graph path that includes character sheets, places, session notes, source documents, and derived lore relationships.

## Migration Steps

1. Keep `Test Fixture` as the locked baseline until `Structured_Knowledge_Graph_Full.png` can be reproduced through the normal UI.
2. Compare `Test Fixture` and `Full Structured Graph` node sets from the same lore directory and classify added nodes as desired, noisy, or duplicate.
3. Promote desired place/session-note nodes into stable typed categories instead of allowing them to appear as accidental secondary characters.
4. Add filtering or normalization rules for noisy extracted nodes before they reach `Full Structured Graph`.
5. Add regression coverage for the accepted full structured node set, then regenerate the full structured screenshot under a new screenshot name.
6. After the full graph is stable, decide whether `Test Fixture` remains as a diagnostic view or moves behind an e2e-only flag.

## Immediate Next Check

Run the app with current lore and compare:

- `Test Fixture`: should show only character-sheet-derived nodes.
- `Full Structured Graph`: should additionally show source/place/session-note-derived nodes such as `Family Tree`.
